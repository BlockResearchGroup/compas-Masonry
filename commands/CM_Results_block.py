#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Results_block — the result data of the blocks you select.

Results_print reports the whole set; this answers "what happened to *this*
block": its displacement, and every contact it takes part in, with the force,
stress and opening at each — including which neighbour is on the other side.

Selection is by picking blocks in the viewport, resolved to graph nodes through
the persistent `element_guid` User Text tag (never by object name, which a
redraw does not preserve).

Four outputs, chosen together at the end rather than one at a time — any
combination is legal, and asking four times for what is one decision is the
prompt-chaining this plugin avoids everywhere else:

- **Print** — a table per selected block in the command window.
- **Tag** — the same numbers written onto the block's Rhino object as User Text,
  so they show in the properties panel and survive being saved with the file.
  Cleared and rewritten on each run, and removed if you pick a different result.
- **CSV** — the same numbers again, one row per (block, contact), for a
  spreadsheet. The rows are built by `results.block_result_rows` from the very
  same report the table prints, so the file and the screen cannot disagree.
- **Isolate** — hide every other block and every result force that does not touch
  a selected one, so the view can be exported as a picture of this block alone.
  Boundary-condition arrows are not filtered (see `isolate`).
  `Session_redraw` brings the rest back; nothing else does.
"""

import csv
import json
import pathlib

import rhinoscriptsyntax as rs  # type: ignore

import compas_rhino.objects
from compas_dem.models import BlockModel
from compas_masonry.inputs import Options
from compas_masonry.results import CSV_HEADER
from compas_masonry.results import FORCE_UNIT
from compas_masonry.results import STRESS_UNIT
from compas_masonry.results import block_displacements
from compas_masonry.results import block_result_rows
from compas_masonry.results import contact_openings
from compas_masonry.results import contact_resultants
from compas_masonry.results import face_stresses
from compas_masonry.results import to_force_unit
from compas_masonry.results import to_stress_unit
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import warn

# User Text keys this command owns, so a re-run can clear its own tags without
# touching element_guid / material_name / is_support.
TAG_KEYS = ["result_key", "result_displacement", "result_contacts", "result_force_total"]


def choose_result(session, problem_name):
    """Pick one stored result set. Returns (key, results) or None."""
    stored = (session.get("results") or {}).get(problem_name) or {}
    if not stored:
        warn(f"No results stored for {problem_name}. Run Problem_solve first.")
        return None

    keys = sorted(stored)
    if len(keys) == 1:
        return keys[0], stored[keys[0]]

    key = rs.ListBox(keys, message="Result set", title="Results")
    if not key:
        return None
    return key, stored[key]


def selected_blocks(session, model):
    """Select Rhino objects and resolve them to (node, guid) pairs."""
    guids = compas_rhino.objects.select_objects(message="Select the blocks to report on")
    if not guids:
        return []

    guid_element_map = session.guid_element_map(model)
    out = []
    for guid in guids:
        node = session.find_node(guid, guid_element_map)
        if node is not None:
            out.append((node, guid))
    return sorted(set(out))


def block_report(node, displacements, stresses, openings, resultants):
    """Everything known about one block in this result set."""
    contacts = []
    for _, vector, magnitude, edge in resultants:
        if node not in edge:
            continue
        other = edge[1] if edge[0] == node else edge[0]
        label = f"{edge[0]}-{edge[1]}"
        contacts.append(
            {
                "with": other,
                "label": label,
                "force": vector,
                "magnitude": magnitude,
                "stress": stresses.get(label),
                "opening": openings.get(label),
            }
        )
    contacts.sort(key=lambda c: -c["magnitude"])

    return {
        "node": node,
        "displacement": displacements.get(node),
        "contacts": contacts,
        "force_total": sum(c["magnitude"] for c in contacts),
    }


def print_report(report) -> None:
    node = report["node"]
    print(f"\n--- block {node} ---")

    displacement = report["displacement"]
    if displacement is None:
        print("displacement : - (this solver returned no displacements)")
    else:
        magnitude, translation, label = displacement
        print(f"displacement : |u| = {magnitude:.6g}   [{translation[0]:.6g}, {translation[1]:.6g}, {translation[2]:.6g}]   ({label})")

    if not report["contacts"]:
        print("contacts     : none carrying force")
        return

    print(f"contacts     : {len(report['contacts'])}, total |F| = {to_force_unit(report['force_total']):.6g} {FORCE_UNIT}")
    # Units in the column heads, and the same conversion the CSV and the Rhino
    # tags use — this table and `block_result_rows` describe the same contacts.
    header = (
        f"  {'with':<8}{'|F| [' + FORCE_UNIT + ']':>14}{'Fx [' + FORCE_UNIT + ']':>14}"
        f"{'Fy [' + FORCE_UNIT + ']':>14}{'Fz [' + FORCE_UNIT + ']':>14}"
        f"{'stress [' + STRESS_UNIT + ']':>16}{'opening':>14}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for contact in report["contacts"]:
        force = contact["force"]
        stress = contact["stress"]
        opening = contact["opening"]
        print(
            f"  {contact['with']:<8}{to_force_unit(contact['magnitude']):>14.6g}{to_force_unit(force[0]):>14.6g}"
            f"{to_force_unit(force[1]):>14.6g}{to_force_unit(force[2]):>14.6g}"
            f"{('-' if stress is None else format(to_stress_unit(stress), '.6g')):>16}"
            f"{('-' if opening is None else format(opening, '.6g')):>14}"
        )


def tag_block(session, guid, key, report) -> None:
    """Write the block's result data onto its Rhino object as User Text."""
    displacement = report["displacement"]
    session.set_user_params(
        guid,
        {
            "result_key": key,
            "result_displacement": None if displacement is None else displacement[1],
            "result_contacts": [{"with": c["with"], "force_magnitude": c["magnitude"], "stress": c["stress"], "opening": c["opening"]} for c in report["contacts"]],
            "result_force_total": report["force_total"],
        },
    )


def export_csv(filepath, reports) -> int:
    """Write the reports to `filepath` as CSV. Returns the number of rows written.

    `newline=""` is not optional: without it the csv module's own "\\r\\n" line
    ending is translated again on Windows and every other line comes out blank.
    """
    rows = []
    for report in reports:
        rows.extend(block_result_rows(report))

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)

    return len(rows)


def isolate(session, model, nodes) -> int:
    """Hide every block and force object that does not belong to `nodes`.

    Two different lookups, because the two kinds of object are identified
    differently. A block is found through the persistent `element_guid` User Text
    that `guid_element_map` reads; a force line carries the `edge` this command
    also reports on, written by `set_user_params` when it was drawn.

    Force objects are matched on the edge rather than on the layer, so a contact
    BETWEEN two selected blocks survives while the same block's contacts with its
    hidden neighbours do not.

    Objects with neither tag are left alone: this hides what it recognises rather
    than everything it does not, so a construction line or a title block the user
    put in the document is not swept up in a results view.

    That leaves BOUNDARY-CONDITION arrows on screen, including those of blocks
    being hidden. They carry a `load_kind` User Text but no block index — the
    params `_draw_bc_vector` writes are the force, the point and the loading type
    — so there is nothing here to filter them on.
    # ponytail: BC arrows always survive isolate; tag them with block_index in
    # session.draw_problem_conditions if they need to be filtered too.

    Returns
    -------
    int
        The number of objects hidden.

    """
    guid_element_map = session.guid_element_map(model)

    hide = []
    for guid in rs.AllObjects() or []:
        node = session.find_node(guid, guid_element_map)
        if node is not None:
            if node not in nodes:
                hide.append(guid)
            continue

        edge = rs.GetUserText(guid, "edge")
        if edge:
            try:
                if not set(json.loads(edge)) & nodes:
                    hide.append(guid)
            except ValueError:
                continue

    if not hide:
        return 0
    rs.HideObjects(hide)
    return len(hide)


def ask_output():
    """Which outputs to produce. Returns a dict of flags, or None if cancelled."""
    options = Options("Output")
    options.add_toggle("print", True, off="NoPrint", on="Print", text=True, keyword="Print")
    options.add_toggle("tag", False, off="NoTag", on="Tag", text=True, keyword="Tag")
    options.add_toggle("csv", False, off="NoCsv", on="Csv", text=True, keyword="Csv")
    options.add_toggle("isolate", False, off="KeepAll", on="Isolate", text=True, keyword="View")

    values = options.get()
    if values is None:
        return None

    return {
        "print": values["print"] == "Print",
        "tag": values["tag"] == "Tag",
        "csv": values["csv"] == "Csv",
        "isolate": values["isolate"] == "Isolate",
    }


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        return warn("No existing BlockModel in session. Please create one first.")
    if not session.problems:
        return warn("No problem in session. Run Problem_create first.")

    name = session.choose_problem(message="Problem to report on", keywords=True)
    if name is None:
        return

    picked = choose_result(session, name)
    if picked is None:
        return
    key, results = picked

    blocks = selected_blocks(session, model)
    if not blocks:
        return warn("No block resolved from the selection. Select the block meshes under Masonry::Model.")

    # derived once for the whole set, then filtered per block
    resultants = contact_resultants(results)
    stresses = {label: value for value, _, label in face_stresses(results)}
    openings = {label: value for value, _, label in contact_openings(results)}

    displacements = {}
    for magnitude, translation, _, label in block_displacements(results, model):
        # a body groups several blocks under one transformation
        for token in label.replace("block ", "").replace("body ", "").split("-"):
            if token.isdigit():
                displacements[int(token)] = (magnitude, translation, label)

    output = ask_output()
    if output is None:
        return

    # The file is asked for BEFORE anything is written, so a cancelled save dialog
    # costs nothing. Tagging and isolating both change the document.
    filepath = None
    if output["csv"]:
        filepath = rs.SaveFileName("Export block results", "CSV files (*.csv)|*.csv||", filename=f"{name}_{key}.csv")
        if not filepath:
            return

    print(f"\n=== {key}: {len(blocks)} block(s) ===")
    reports = []
    for node, guid in blocks:
        report = block_report(node, displacements, stresses, openings, resultants)
        reports.append(report)
        if output["print"]:
            print_report(report)
        if output["tag"]:
            tag_block(session, guid, key, report)

    if output["tag"]:
        print(f"\nTagged {len(blocks)} block(s) with their {key} data (visible in the properties panel).")

    if filepath:
        try:
            rows = export_csv(filepath, reports)
        except OSError as e:
            warn(f"Could not write {filepath}: {e}")
        else:
            print(f"Exported {rows} row(s) to {filepath}.")

    if output["isolate"]:
        hidden = isolate(session, model, {node for node, _ in blocks})
        print(f"Isolated {len(blocks)} block(s); hid {hidden} object(s). Session_redraw restores the view.")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
