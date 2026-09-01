#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Model_supports_options — RhinoCommon variant of Model_supports.

Only the Add/Remove/Clear pick changes (command line options instead of
rs.GetString); the support logic is identical. See Model_supports for why
guids are resolved to graph nodes before any redraw.

Supports are copied onto each Problem when it is created, and into each
BoundaryCondition when it is registered — so editing them here leaves every
existing problem holding the old set. Rather than let that drift silently, this
offers to push the new set into the problems (the same thing
Problem_create > RefreshSupports does).
"""

import pathlib

import compas_rhino.objects
from compas_dem.models import BlockModel
from compas_masonry.inputs import choose
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import warn


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        return warn("No existing BlockModel in session. Please create one first.")

    option = choose("Supports", ["Add", "Remove", "Clear"])
    if option is None:
        return

    guid_element_map = session.guid_element_map(model)

    if option in ("Add", "Remove"):
        verb = "add" if option == "Add" else "remove"
        guids = compas_rhino.objects.select_objects(message=f"Select supports you want to {verb}")
        if not guids:
            return
        nodes = {n for n in (session.find_node(g, guid_element_map) for g in guids) if n is not None}
        if not nodes:
            return warn("No blocks resolved from the selection.")
        # after the last bail-out, before the first change: the baseline has to
        # capture the state as it was BEFORE this command, or the first action of
        # a session can never be undone (undo refuses at the oldest record).
        session.ensure_baseline()
        # go through the model's own API rather than setting is_support by hand:
        # supports are a model concern and this is where compas_dem keeps them
        if option == "Add":
            model.add_supports(sorted(nodes))
        else:
            for node in nodes:
                model.remove_support(node)
        print(f"{option}: {len(nodes)} support(s).")

    elif option == "Clear":
        session.ensure_baseline()
        for node in list(model.graph.nodes()):
            if model.graph.node_element(node).is_support:
                model.remove_support(node)
        print("Cleared all supports.")

    session.save_model()
    session.sync_support_layers()
    session.redraw()
    session.record(f"Supports: {option}")


# `refresh_problems` lived here. Supports used to be copied onto every Problem at
# creation and into every BoundaryCondition at registration, so editing them here
# left stale copies behind and this command had to offer to re-import them. Since
# the 2026-08 compas_dem restructure supports live only on the model and the
# solvers read `Block.is_support` directly, so there is nothing to refresh — and
# the prompt that fired on a first run, before any support existed, is gone with it.


if __name__ == "__main__":
    RunCommand()
