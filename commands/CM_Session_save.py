#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Session_save — save the whole session to a single JSON file.

Saving and loading work the way RhinoVAULT's do: there is ONE thing to save and
ONE thing to open, the session. The per-artefact commands this replaced
(Model_export, Model_import, Problem_export) are gone — they wrote fragments
that could not be opened back into a working session on their own, and gave
three answers to "how do I save my work".

What is written: the `Analysis` — the model together with every problem and its
boundary conditions — plus the active problem name and the display settings.

The Analysis is what makes one key enough. A Problem serializes as a guid
REFERENCE to its model, so a file holding them separately has to hand the model
back to every problem on the way in; `Analysis.__from_data__` does that itself.

Solver results are excluded by default. They can be included wholesale, or
selected from a hierarchy of problems and solve runs, and are then embedded in
the portable session file.

Re-open with Session_import. Files written before 2026-08-07 carried separate
`blockmodel` and `problems` keys and are NOT readable — Session_import says so
rather than importing half of one.
"""

import pathlib

import rhinoscriptsyntax as rs  # type: ignore

import compas
from compas_masonry.session import MasonrySession as Session
from compas_masonry.sessionio import selected_results
from compas_rui.feedback import warn
from compas_rui.forms import FileForm


def session_data(session, results=None) -> dict:
    """Collect the exportable session state."""
    data = {
        "analysis": session.analysis,
        "active_problem": session.active_problem_name,
    }
    if results is not None:
        data["results"] = results

        # WHICH results were on screen, so an import restores the view and not
        # just the data. Filtered to what is actually being exported: recording
        # the intent to draw a result the file does not carry would make the
        # import replay a view it cannot fill. `draw_shown_results` skips unknown
        # keys anyway, but a session file should not describe what is not in it.
        shown = session.get("shown_results") or {}
        kept = {}
        for problem_name, view in shown.items():
            exported_keys = [key for key in view.get("keys", []) if key in (results.get(problem_name) or {})]
            if exported_keys:
                kept[problem_name] = dict(view, keys=exported_keys)
        if kept:
            data["shown_results"] = kept

    # settings are pydantic, not compas Data
    try:
        data["settings"] = session.settings.model_dump()
    except Exception as e:
        print(f"Settings not exported ({e}).")

    return data


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    if session.model is None and not session.problems:
        return warn("Nothing to export: the session has no BlockModel and no problem.")

    path = rs.DocumentPath()  # to make sure the document has a path
    basedir = pathlib.Path(path).parent if path else pathlib.Path().home()

    stored = session.get("results") or {}
    exported_results = None
    if stored:
        result_mode = rs.ListBox(
            ["Do not include results", "Include all results", "Select results to include"],
            message="Solver results in exported session",
            title="Save Session",
            default="Do not include results",
        )
        if result_mode is None:
            return
        if result_mode == "Include all results":
            # `stored` is already the {problem: {key: result}} shape the session
            # file wants, so "all" is the whole mapping and needs no selection
            # pass. Kept distinct from the default rather than made the default:
            # results are the bulky part of an exported session.
            exported_results = stored
        elif result_mode == "Select results to include":
            from compas_masonry.forms.results import ResultSelectionForm

            selection = ResultSelectionForm(stored).show()
            if selection is None:
                return
            exported_results = selected_results(stored, selection)

    filepath = FileForm.save(str(basedir), "Masonry_session.json")
    if not filepath:
        return

    data = session_data(session, results=exported_results)

    try:
        compas.json_dump(data, filepath)
    except Exception as e:
        return warn(f"Export failed: {e}")

    analysis = data["analysis"]
    names = [problem.name for problem in analysis.problems]
    print(f"Exported session to {filepath}")
    print(f"  blockmodel: {'yes' if analysis.model is not None else 'no'}")
    print(f"  problems  : {len(names)} ({', '.join(names) or '-'})")
    count = sum(len(runs) for runs in (exported_results or {}).values())
    print(f"  results   : {count if exported_results is not None else 'not included'}")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
