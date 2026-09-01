#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Model_contacts_options — RhinoCommon variant of Model_contacts.

Tolerance and minimum contact area are asked together as command line options
instead of one after the other.
"""

import pathlib

import rhinoscriptsyntax as rs  # type: ignore

import compas_rhino.layers
from compas_dem.interactions import EdgeContact
from compas_dem.interactions import FrictionContact
from compas_dem.interactions import VertexContact
from compas_dem.models import BlockModel
from compas_masonry.inputs import Options
from compas_masonry.session import MasonrySession as Session
from compas_model.models import InteractionGraph
from compas_rui.feedback import confirm
from compas_rui.feedback import warn

# EdgeContact and VertexContact (degenerate, post-displacement contacts) are
# plain Data subclasses, NOT subclasses of FrictionContact — so looking for
# FrictionContact alone leaves their scene objects behind, and clearing the
# layer under them strands guids the scene still tracks.
CONTACT_TYPES = (FrictionContact, EdgeContact, VertexContact)


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        warn("No block model in the session.")
        return

    # =============================================================================
    # Stored results do not survive this
    # =============================================================================

    # Recomputing contacts rebuilds the interaction graph, and a Results is keyed
    # by graph node index and by "u,v" edge strings — so results from the old
    # graph would stay in the session describing edges that no longer exist,
    # still matching on `model_id` because it IS the same model. Nothing would
    # report a mismatch: `draw_results` looks up `results.transformation(
    # block.graphnode)` by the block's CURRENT index, so shifted numbering draws
    # another block's transformation as if it were correct.
    #
    # Asked BEFORE anything is touched, deliberately. The teardown below removes
    # every interaction *before* the tolerance prompt, so a confirmation placed
    # any later would leave the model with no contacts when the user says no.
    count = session.count_results()
    plural = "s" if count != 1 else ""
    if count and not confirm(f"Recomputing contacts invalidates the {count} stored result set{plural}, which will be deleted along with anything drawn from them. Continue?"):
        return

    # The last bail-out is above; from here the command always changes something,
    # so this is where the pre-change baseline belongs — including the result
    # deletion just below, which must itself be undoable.
    session.ensure_baseline()

    if count:
        session.clear_results()
        print(f"Deleted {count} stored result set{plural} — the graph they described is gone.")

    # clear() deletes each object's drawn geometry while its guids are still
    # valid; removing without clearing first strands those guids in the scene.
    for obj in list(session.scene.objects):
        item = getattr(obj, "item", None)
        if isinstance(item, CONTACT_TYPES) or isinstance(item, InteractionGraph):
            obj.clear()
            session.scene.remove(obj)

    # sweep anything drawn on these layers that the scene no longer tracks
    compas_rhino.layers.clear_layer("Masonry::Model::Interactions")
    compas_rhino.layers.clear_layer("Masonry::Model::Contacts")

    # this should be simplified in the future
    # by adding a method model.clear_interactions()
    for u, v in list(model.graph.edges()):
        a = model.graph.node_element(u)  # type: ignore
        b = model.graph.node_element(v)  # type: ignore
        model.remove_interaction(a, b)

    session.redraw()
    rs.Redraw()

    # =============================================================================
    # Ask for input
    # =============================================================================

    # titles, defaults and ge/le bounds come from BlockModelSettings, so they are
    # declared once (compas_masonry/settings.py) and rendered here. As in
    # Model_contacts, the values are used for this run only, not written back.
    options = Options.from_model(
        session.settings.blockmodel,
        prompt="Contact detection",
        include=["contact_tolerance", "contact_minimum_area"],
    )

    values = options.get()
    if values is None:
        return

    # =============================================================================
    # Compute contacts
    # =============================================================================

    model.compute_contacts(tolerance=values["contact_tolerance"], minimum_area=values["contact_minimum_area"])

    # `compute_contacts` mutates the model IN PLACE, and the session is a cache in
    # front of files: only `set()` writes. Without this the interaction graph never
    # reached disk — every snapshot `record()` takes below, and every reload after a
    # restart, came back with the blocks but ZERO contacts, so the next solve
    # reported "No contacts in the model" on a model that visibly had them.
    # See wiki_session_primer.md §8.2.
    session.save_model()

    # =============================================================================
    # Update scene
    # =============================================================================

    session.scene.add(model.graph, layer="Masonry::Model::Interactions")  # type: ignore

    for contact in model.contacts():
        session.scene.add(contact, layer="Masonry::Model::Contacts")  # type: ignore

    session.redraw()

    rs.Redraw()
    session.record("Contacts")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
