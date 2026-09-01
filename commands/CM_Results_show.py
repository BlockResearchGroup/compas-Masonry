#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Results_show_options — draw a stored result set.

- Follows Problem_solve. No result geometry is in the document until this
  command runs.
- Results are stored per solve, keyed by solver and timestamp
  ("RBE_2026-08-04T15-30-12"), and drawn at PROBLEM level:
  "Masonry::<i>_<problem>::Results::<key>".

  A problem IS the load case, so a result belongs to the problem. The timestamp
  means a re-solve after changing a material or a contact law is kept beside the
  earlier run instead of overwriting it.

Two kinds of result, because the solvers answer different questions:

- **Forces** — contact resultants and contact geometry. This is what CRA and RBE
  produce: `_post_processing_cra` stores an IDENTITY transformation for every
  block and puts the whole answer on the contact edges.
- **Displaced** — a displaced copy of each block from `Results.transformation`,
  exaggerated by `Results.displacement_scale` (fed from
  settings.blockmodel.scale_displacement). This is the LMGC90 shape.

So Displaced is only offered for a solver that produces displacements, read off
the result key rather than off the problem's current solver — the setting may
have changed since the solve, the key cannot. `moves_anything` stays as the
fallback for a result whose key does not name a known solver.
"""

import pathlib
import time

import rhinoscriptsyntax as rs  # type: ignore

from compas_dem.models import BlockModel
from compas_masonry.inputs import choose
from compas_masonry.inputs import set_display_mode
from compas_masonry.results import application_point_report
from compas_masonry.results import tension_report
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import warn

# Solvers that move blocks. CRA and RBE answer on the contact edges and store an
# identity transformation per block, so a Displaced view of one of their results
# stacks an exact copy of the model on itself and reads as a no-op.
DISPLACEMENT_SOLVERS = ("LMGC90", "3DEC")


def stored_results(session, problem_name) -> dict:
    """The results stored for a problem, keyed by result key ("RBE_2026-08-04T15-30-12")."""
    return (session.get("results") or {}).get(problem_name) or {}


def solver_of(key) -> str:
    """The solver named by a result key: "RBE_2026-08-04T15-30-12" -> "RBE"."""
    return key.split("_")[0] if key else ""


def offers_displacement(keys, results, model) -> bool:
    """Whether Displaced is worth offering for the selected result sets.

    Decided by the solver named in the key, not by the problem's current solver:
    Problem_setsolver may have been run since, and re-pointing it at LMGC90 does not
    retroactively give an RBE result any displacements.
    """
    for key in keys:
        if solver_of(key) in DISPLACEMENT_SOLVERS:
            return True
    # a key that names no known solver (hand-built, or a solver added later):
    # fall back to asking the result itself
    unknown = [k for k in keys if solver_of(k) not in DISPLACEMENT_SOLVERS + ("CRA", "RBE")]
    return any(moves_anything(results[k], model) for k in unknown)


def moves_anything(results, model) -> bool:
    """True if any block carries a non-identity transformation.

    CRA/RBE store an identity per block, so this separates a force result from a
    displacement result without asking which solver ran. Read through
    `node_attribute` rather than `transformation()`, to skip the
    displacement_scale amplification.
    """
    for block in model.elements():
        T = results.node_attribute(block.graphnode, "transformation")
        if T is None:
            continue
        matrix = T.matrix if hasattr(T, "matrix") else T
        for i, row in enumerate(matrix):
            for j, value in enumerate(row):
                expected = 1.0 if i == j else 0.0
                if abs(value - expected) > 1e-12:
                    return True
    return False


def report_forces(results) -> None:
    """Print the force magnitudes, so there is a number to sanity-check."""
    magnitudes = [m for m in (results.force_magnitude(edge) for edge in results.edges()) if m]
    if not magnitudes:
        return
    print(f"  {len(magnitudes)} contact resultant(s): max {max(magnitudes):.4g}, total {sum(magnitudes):.4g}")

    # Ahead of the tension block, which returns early when there is no tension.
    # A force drawn at the joint centroid looks exactly like a force drawn where
    # it acts, so this is the only place the difference is ever visible.
    misplaced = application_point_report(results)
    if misplaced:
        warn(misplaced)

    # Said here as well as in Problem_solve: a result can be drawn any number of
    # times, and days after it was solved.
    reported = tension_report(results)
    if reported is None:
        return
    expected, message = reported
    if expected:
        print(f"  {message}")
    else:
        warn(message)
    print("  Session_settings > BlockModel > Show Corner Forces draws where it is.")


def show(session, model, problem_name, key, results, mode, redraw=True) -> None:
    base = session.results_layer(problem_name, key)

    drew_anything = False

    if mode in ("Forces", "Both"):
        drawn = session.draw_result_forces(problem_name, results, model, key=key, redraw=redraw)
        if drawn:
            print(f"{key}: drew {drawn} contact resultant(s) under {base}::Forces")
            report_forces(results)
            drew_anything = True
        else:
            available = session._result_resultants(results)
            if available:
                warn(f"{key}: contact forces exist, but the active force display settings produced no visible objects.")
            else:
                warn(f"{key}: the stored result carries no contact forces.")

    if mode in ("Displaced", "Both"):
        drawn = session.draw_results(problem_name, results, model, key=key, redraw=redraw)
        if drawn:
            print(f"{key}: drew {drawn} displaced block(s) under {base}::Displaced (scale {session.settings.blockmodel.scale_displacement}).")
            drew_anything = True
        else:
            warn(f"{key}: the stored result has no transformation for any block of the model.")

    if not drew_anything:
        warn(f"{key}: nothing was drawn.")


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        return warn("No existing BlockModel in session. Please create one first.")
    if not session.problems:
        return warn("No problem in session. Run Problem_create first.")

    name = session.choose_problem(message="Problem to show results for", keywords=True)
    if name is None:
        return

    results = stored_results(session, name)
    if not results:
        return warn(f"No results stored for {name}. Run Problem_solve first.")

    keys = sorted(results)
    if len(keys) == 1:
        selected = keys
    else:
        picked = rs.MultiListBox(keys, message="Result set(s) to draw", title="Results")
        if not picked:
            return
        selected = list(picked)

    # Only offer Displaced for a solver that produces displacements. For a
    # CRA/RBE set there is nothing to choose, so do not ask at all.
    if offers_displacement(selected, results, model):
        # A 3DEC result carries both transformations and contact forces. Forces
        # are the useful first view and are substantially cheaper than creating
        # a displaced mesh for every block; LMGC90 remains displacement-first.
        default_mode = "Forces" if all(solver_of(key) == "3DEC" for key in selected) else "Displaced"
        mode = choose("Draw", ["Forces", "Displaced", "Both"], default=default_mode)
        if mode is None:
            return
    else:
        mode = "Forces"
        print(f"{solver_of(selected[0])} reports contact forces, not displacements — drawing forces.")

    # after the last bail-out, before the first change — see Session_undo
    # Persisted settings from an older session can override the current defaults
    # and leave every force category disabled. If the user explicitly asks for
    # Forces or Both, make the canonical force views visible.
    force_settings = session.settings.blockmodel
    # EVERY force view belongs in here. A view left out is a view that, on its
    # own, still reads as "all force views are disabled" — so asking for Forces
    # with only that one enabled would switch resultants and reactions back on
    # over the user's explicit choice, and persist it at the `record()` below.
    # `test_every_force_view_is_counted_as_one` pins this against the settings.
    force_views = (
        force_settings.show_resultants,
        force_settings.show_reactions,
        force_settings.show_normalforces,
        force_settings.show_frictionforces,
        force_settings.show_horizontalforces,
        force_settings.show_verticalforces,
        force_settings.show_selfweight,
        force_settings.show_cornerforces,
    )
    # ponytail: this WRITES the user's settings, it does not override them for one
    # draw. `session.record()` at the end of this command persists
    # `settings.model_dump()`, so asking to view forces once permanently flips
    # show_resultants and show_reactions on disk. Reviewed 2026-08-31 and
    # deliberately KEPT: the case only fires when every force view is off, where
    # the alternative is drawing nothing and looking broken, and making it stick
    # means the next Results_show behaves the same way.
    #
    # Known ceiling: a user who switched those two off on purpose gets them back
    # and is not told the setting changed, only that it was "enabled ... for this
    # result view" — which is not what happened. Upgrade path is a temporary
    # override: copy `force_settings`, flip the copy, draw from it, leave the
    # session's own settings alone. Deferred, not forgotten.
    if mode in ("Forces", "Both") and not any(force_views):
        force_settings.show_resultants = True
        force_settings.show_reactions = True
        print("All force views were disabled; enabled resultants and reactions for this result view.")

    session.ensure_baseline()

    # Adding each mesh, layer assignment, colour and User Text field is a
    # separate Rhino document change. Batch all selected result geometry and
    # repaint once instead of repainting the growing document object by object.
    rs.EnableRedraw(False)
    drawing_started = time.perf_counter()
    try:
        for key in selected:
            result_started = time.perf_counter()
            show(session, model, name, key, results[key], mode, redraw=False)
            print(f"{key}: Rhino drawing completed in {time.perf_counter() - result_started:.2f}s.")
    finally:
        rs.EnableRedraw(True)
        rs.Redraw()
    print(f"Result visualisation completed in {time.perf_counter() - drawing_started:.2f}s.")

    # Record WHAT is on screen. Solving draws nothing and this command's choices
    # (which keys, and Forces/Displaced/Both) exist nowhere else — so without this
    # an undo, which clears the whole layer tree before redrawing, silently threw
    # the result view away with no means of rebuilding it. Kept per problem, so
    # showing results for a second problem does not forget the first.
    shown = session.get("shown_results") or {}
    shown[name] = {"keys": list(selected), "mode": mode}
    session["shown_results"] = shown

    # Set and LEFT set: the point is to leave the user looking at the result, so
    # this is not the restoring `display_mode` context manager the pickers use.
    # NOT named `mode` — that is the Forces/Displaced/Both choice, and `record`
    # below reports it.
    viewport = session.settings.blockmodel.results_display_mode
    if set_display_mode(viewport):
        print(f"Viewport switched to {viewport} so the results read against the blocks (Session_settings > BlockModel).")

    # Showing results IS a state change, because `shown_results` above is the only
    # record of what is on screen. Without recording here it never reaches a
    # snapshot, and the first undo deletes it along with the rest of the working
    # copy — which is exactly how the result view went missing the first time.
    session.record(f"Show results: {name} ({mode})")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
