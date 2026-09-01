#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Problem_loads — add and remove loads on a Problem.

Renamed from Problem_addload, and rebuilt on the 2026-08 compas_dem API.

**A load belongs to a boundary condition group.** compas_dem's
`BoundaryConditionGroup` collects the conditions that act together; a problem
holds several, and solving applies all of them. The group is chosen in the same
window as the load itself: pick an existing one to extend it, or New to start
another. Each group gets its own layer under "…::BoundaryConditions::<group>".

**Only LOAD groups are offered here**, and Problem_displacements offers only the
displacement ones — so the two kinds never share a group. That split is a plugin
convention enforced in these two commands and in `boundaryconditions.group_kind`;
compas_dem itself is happy to hold both in one group, and a group built from a
script that does is drawn correctly and simply offered in one of the two.

Load types:

- **Point** — a force at a **vertex** or at the **centroid of a face**. compas_dem
  also offers an arbitrary point and the block centroid; the Rhino UI
  deliberately offers only these two (the summer-school decision), since they are
  the two a user can actually see and click.
- **Surface** — a traction on faces. compas_dem multiplies by the face area, so
  this is a pressure, not a total force.
- **Moment** — a couple with no net force.
- **BodyForce** — an acceleration applied to every block by its mass: a rotated
  gravity for a tilted table, or a static seismic load. Gravity itself is applied
  by the solver from block density, so this carries only the ADDED component.

**Selection is the geometry, and it is not limited to one block.** Point and
Surface pick the vertices/faces themselves in the viewport, across as many blocks
as you like in a single call; Moment picks whole blocks the same way. Every
anchor picked gets the same load. This replaced typing a face or vertex INDEX
read off a temporary TextDot, which could only reach one block per call — see
`inputs.pick_block_components` for why the picked component is matched by
POSITION rather than by index.

The two translational loads take their vector one of two ways, chosen with the
**Direction** option: `Type` asks for the three components, `Draw` asks for a
magnitude and then has the direction picked in the viewport. The drawn LENGTH is
discarded — see `inputs.pick_direction` for why a line length cannot be a force.
The direction is picked AFTER the anchors, so the geometry it acts on is on
screen while it is drawn. Moment and BodyForce are components-only: a moment's
vector is a rotation axis, and drawing one reads as a movement.

Two things that used to be here and are gone:

- **Gravity is not a load.** `bc.g` never did anything — self-weight is applied
  unconditionally from block density — so there is no Gravity option and no
  gravity arrow to clear.
- **BodyForce is no longer expanded by hand.** It used to be written as one
  centroid point load per block, because `add_global_body_force` was not
  honoured by the solvers. `resolve_centroidal_loads` now handles `BodyForce`
  natively and mass-weights it, so the expansion (and the `AllPoint` removal it
  forced) is deleted.
"""

import pathlib

import rhinoscriptsyntax as rs  # type: ignore

import compas_rhino.objects
from compas_dem.models import BlockModel
from compas_masonry.boundaryconditions import describe
from compas_masonry.boundaryconditions import group_names
from compas_masonry.boundaryconditions import groups_of_kind
from compas_masonry.boundaryconditions import loads_of
from compas_masonry.boundaryconditions import next_group_name
from compas_masonry.boundaryconditions import remove_condition
from compas_masonry.boundaryconditions import remove_group
from compas_masonry.inputs import Options
from compas_masonry.inputs import choose
from compas_masonry.inputs import pick_block_components
from compas_masonry.inputs import pick_direction
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import warn

NEW = "New"


def selected_nodes(session, model, message):
    """Select Rhino block objects and resolve them to graph node indices."""
    guids = compas_rhino.objects.select_objects(message=message)
    if not guids:
        return []
    guid_element_map = session.guid_element_map(model)
    return sorted({n for n in (session.find_node(g, guid_element_map) for g in guids) if n is not None})


def pick_anchors(session, model, what, message):
    """Pick faces or vertices in the viewport, across any number of blocks.

    Replaces the old flow — select ONE block, then read its face/vertex INDEX off
    a temporary TextDot and type it — which could only ever load one block per
    command call and asked the user to transcribe a number they had no way to
    verify. Selection is now the geometry itself, and one call covers as many
    blocks as are picked.

    Returns
    -------
    list[tuple] or None
        Sorted (node, key) pairs, or None if cancelled.

    """
    guid_element_map = session.guid_element_map(model)
    blocks = {}

    def mesh_of(guid):
        node = session.find_node(guid, guid_element_map)
        if node is None:
            return None
        blocks[str(guid)] = node
        return model.graph.node_element(node).modelgeometry

    # faces want a surface to click, vertices want the shading out of the way —
    # both configurable in Session_settings > BlockModel
    mode = getattr(session.settings.blockmodel, f"pickmode_{what}", None)
    picked = pick_block_components(what, mesh_of, message, mode=mode)
    if not picked:
        return None

    anchors = sorted((blocks[str(guid)], key) for guid, keys in picked.items() for key in keys)
    if not anchors:
        warn(f"Nothing selected belongs to the block model, so no {what} was loaded.")
        return None
    return anchors


def load_is_empty(values):
    """True if the load as specified would be zero, whichever way it was given.

    Checked in `ask_load`, before any selection. Asking the user to pick a block,
    an anchor and then a direction, and only then refusing the load because every
    component was left at zero, is the kind of thing that makes a command feel
    hostile. Kinds without a translational vector (Moment, BodyForce) validate
    themselves in `add_load` and are not this function's business.
    """
    prefix = {"Point": "f", "Surface": "t"}.get(values["kind"])
    if prefix is None:
        return False
    if values["direction"] == "Draw":
        return not values[f"{prefix}mag"]
    return not any(values[f"{prefix}{axis}"] for axis in ("x", "y", "z"))


def load_vector(values, prefix, message):
    """The load vector: typed components, or a drawn direction times a magnitude.

    `prefix` is "f" for a force and "t" for a traction, naming the fields
    `ask_load` declared for that kind. Returns None if the direction pick was
    cancelled, so the caller bails out without writing anything.
    """
    if values["direction"] == "Draw":
        direction = pick_direction(message)
        if direction is None:
            return None
        return [component * values[f"{prefix}mag"] for component in direction]

    return [values[f"{prefix}{axis}"] for axis in ("x", "y", "z")]


def ask_load(problem):
    """Ask for the group and every load field in one window.

    The group field is what makes "extend or start a new one" a choice rather
    than a separate prompt: pick an existing group to add to it, or New and give
    a name.
    """

    def is_(*kinds):
        return lambda v: v["kind"] in kinds

    # A translational load is given EITHER as three components OR as a direction
    # drawn in the viewport times a magnitude. `values` carries every field
    # whether or not it is visible, so "direction" is always readable here.
    def typed(*kinds):
        return lambda v: v["kind"] in kinds and v["direction"] == "Type"

    def drawn(*kinds):
        return lambda v: v["kind"] in kinds and v["direction"] == "Draw"

    existing = group_names(problem, "load")
    choices = [NEW] + existing

    options = Options("Add load")
    options.add_list("group", choices, keyword="Group")
    options.add_text("newgroup", next_group_name(problem, "load"), keyword="Name", visible=lambda v: v["group"] == NEW)

    options.add_list("kind", ["Point", "Surface", "Moment", "BodyForce"], keyword="LoadType")

    # where a point load acts. compas_dem also has at_point and at_centroid; only
    # the two a user can see and click are offered here.
    options.add_list("anchor", ["Vertex", "Face"], keyword="At", visible=is_("Point"))

    # Type the components, or draw the direction in the viewport and type only a
    # magnitude. Only the two translational loads offer it: a moment's vector is
    # a rotation AXIS, and drawing one reads as a movement.
    options.add_list("direction", ["Type", "Draw"], keyword="Direction", visible=is_("Point", "Surface"))

    options.add_number("fx", 0.0, keyword="Fx", units="N", prompt="Force fx", visible=typed("Point"))
    options.add_number("fy", 0.0, keyword="Fy", units="N", prompt="Force fy", visible=typed("Point"))
    options.add_number("fz", -1000.0, keyword="Fz", units="N", prompt="Force fz", visible=typed("Point"))
    options.add_number("fmag", 1000.0, keyword="Magnitude", units="N", prompt="Force magnitude", visible=drawn("Point"))

    # a traction: compas_dem multiplies by the face area, so this is a pressure
    options.add_number("tx", 0.0, keyword="Tx", units="N/m2", prompt="Traction tx", visible=typed("Surface"))
    options.add_number("ty", 0.0, keyword="Ty", units="N/m2", prompt="Traction ty", visible=typed("Surface"))
    options.add_number("tz", -1000.0, keyword="Tz", units="N/m2", prompt="Traction tz", visible=typed("Surface"))
    options.add_number("tmag", 1000.0, keyword="Magnitude", units="N/m2", prompt="Traction magnitude", visible=drawn("Surface"))

    options.add_number("mx", 0.0, keyword="Mx", units="Nm", prompt="Moment mx", visible=is_("Moment"))
    options.add_number("my", 0.0, keyword="My", units="Nm", prompt="Moment my", visible=is_("Moment"))
    options.add_number("mz", 0.0, keyword="Mz", units="Nm", prompt="Moment mz", visible=is_("Moment"))

    options.add_number("ax", 0.0, keyword="Ax", units="m/s2", prompt="Acceleration ax", visible=is_("BodyForce"))
    options.add_number("ay", 0.0, keyword="Ay", units="m/s2", prompt="Acceleration ay", visible=is_("BodyForce"))
    options.add_number("az", 0.0, keyword="Az", units="m/s2", prompt="Acceleration az", visible=is_("BodyForce"))

    # time-series shape, straight from the compas_dem load classes
    options.add_toggle("loading", False, off="Ramp", on="Instantaneous", text=True, keyword="Loading")

    values = options.get()
    if values is None:
        return None

    # `group` stays the SELECTOR (either NEW or an existing group's name) and
    # `newgroup` carries the normalized name. Writing the name into `group` here —
    # which is what the name-as-group version did, when a group was only ever a
    # string — makes `resolve_group` look for an existing group called "Load_1"
    # that has not been created yet, and refuse every new group.
    if values["group"] == NEW:
        name = values["newgroup"].strip()
        if not name:
            warn("A load group needs a name.")
            return None
        values["newgroup"] = name

    if load_is_empty(values):
        what = "magnitude" if values["direction"] == "Draw" else "value"
        warn(f"A {values['kind'].lower()} load needs a non-zero {what}.")
        return None

    return values


def resolve_group(problem, values):
    """The BoundaryConditionGroup to write into: an existing one, or a new one.

    Called at the LAST moment, after every prompt the user could still cancel at.
    `add_boundary_condition` registers the group immediately, so creating it up
    front and then cancelling the block selection would leave an empty group —
    and an empty group is not harmless: it takes the name, and `group_kind` has
    to guess its kind from that name.
    """
    name = values["group"]

    if name != NEW:
        for group in groups_of_kind(problem, "load"):
            if group.name == name:
                return group
        warn(f"Load group [{name}] is no longer on this problem.")
        return None

    try:
        return problem.add_boundary_condition(values["newgroup"])
    except ValueError as e:
        # names are unique across the whole problem, displacement groups included
        warn(str(e))
        return None


def add_load(session, model, problem, values):
    """Build the load object(s) and register them on the problem.

    Everything goes through `Problem.add_*`, which resolves anchors against the
    model geometry and writes into the group. There is no load class to import
    here any more: a `PointLoad` at a vertex is `add_point_load_at_vertex`, and a
    moment is `add_moment` (a PointLoad with a zero force, not a class).
    """
    kind = values["kind"]
    loading_type = values["loading"].lower()

    if kind == "BodyForce":
        acceleration = [values["ax"], values["ay"], values["az"]]
        if not any(acceleration):
            warn("A body force needs a non-zero acceleration.")
            return False
        group = resolve_group(problem, values)
        if group is None:
            return False
        problem.add_global_body_force(*acceleration, loading_type=loading_type, boundary_condition=group)
        print(f"Added body force {acceleration} m/s2 to [{group.name}] — applied to every block by its mass.")
        print("  Gravity is applied by the solver from block density, so this is the ADDED component only.")
        return True

    if kind == "Moment":
        nodes = selected_nodes(session, model, "Select block(s) for the moment")
        if not nodes:
            return False
        moment = [values["mx"], values["my"], values["mz"]]
        if not any(moment):
            warn("A moment needs a non-zero value.")
            return False
        group = resolve_group(problem, values)
        if group is None:
            return False
        for node in nodes:
            problem.add_moment(block_index=node, moment=moment, loading_type=loading_type, boundary_condition=group)
        print(f"Added moment {moment} Nm on {len(nodes)} block(s) to [{group.name}].")
        return True

    if kind == "Point":
        what = "vertex" if values["anchor"] == "Vertex" else "face"
        anchors = pick_anchors(session, model, what, f"Select the {what}(s) to load, on any number of blocks")
        if not anchors:
            return False

        # AFTER the anchors, so a drawn direction is picked with the geometry it
        # acts on already on screen. Emptiness was checked in `ask_load`.
        force = load_vector(values, "f", f"Force direction for {len(anchors)} {what}(s): pick the base point, then the tip")
        if force is None:
            return False

        group = resolve_group(problem, values)
        if group is None:
            return False

        # every anchor is resolved to a point HERE, against the geometry as it is
        # now — compas_dem stores the coordinates, not the vertex/face index
        add = problem.add_point_load_at_vertex if what == "vertex" else problem.add_point_load_at_face
        keyword = "vertex_index" if what == "vertex" else "face_index"
        for node, key in anchors:
            add(block_index=node, force=force, loading_type=loading_type, boundary_condition=group, **{keyword: key})
        print(f"Added point load {force} N on {len(anchors)} {what}(s) across {len({n for n, _ in anchors})} block(s) to [{group.name}].")
        return True

    if kind == "Surface":
        anchors = pick_anchors(session, model, "face", "Select the face(s) to load, on any number of blocks")
        if not anchors:
            return False

        # one direction for the whole pick: every face selected here carries the
        # same traction vector, and each keeps its own area when it is resolved
        load = load_vector(values, "t", f"Traction direction for {len(anchors)} face(s): pick the base point, then the tip")
        if load is None:
            return False

        group = resolve_group(problem, values)
        if group is None:
            return False

        # SurfaceLoad takes a single face, so a multi-face pick is one object per
        # face — each keeps its own area when the solver resolves it
        for node, face in anchors:
            problem.add_surface_load(block_index=node, face_index=face, load=load, loading_type=loading_type, boundary_condition=group)
        print(f"Added surface load {load} N/m2 on {len(anchors)} face(s) across {len({n for n, _ in anchors})} block(s) to [{group.name}].")
        print("  A traction is multiplied by the face area, so this is a pressure, not a total force.")
        return True

    return False


def remove_load(problem):
    """Remove loads, either one at a time or a whole group at once.

    Removing a group removes the GROUP OBJECT, not just its contents, so the name
    is free again afterwards. Removing one load leaves the group standing, empty
    if it was the last one — deliberate, so "clear this group and refill it" does
    not lose the name mid-way.
    """
    groups = groups_of_kind(problem, "load")
    if not groups:
        warn("This problem carries no loads.")
        return False

    scope = choose("Remove", ["One", "Group"], default="One")
    if scope is None:
        return False

    names = [group.name for group in groups]

    if scope == "Group":
        name = names[0] if len(names) == 1 else rs.ListBox(names, message="Load group to remove", title="Loads")
        if not name:
            return False
        group = groups[names.index(name)]
        count = len(loads_of(group))
        remove_group(problem, group)
        print(f"Removed group [{name}] and the {count} load(s) in it.")
        return True

    # one flat pick list across every load group, each entry tagged with its group
    entries = [(group, bc) for group in groups for bc in loads_of(group)]
    if not entries:
        warn("This problem carries no loads.")
        return False

    labels = [f"{i}: [{group.name}] {describe(bc)}" for i, (group, bc) in enumerate(entries)]
    label = rs.ListBox(labels, message="Load to remove", title="Loads")
    if not label:
        return False

    group, bc = entries[int(label.split(":")[0])]
    remove_condition(group, bc)
    print(f"Removed {describe(bc)} from [{group.name}]")
    return True


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        return warn("No existing BlockModel in session. Please create one first.")
    if not session.problems:
        return warn("No problem in session. Run Problem_create first.")

    name = session.choose_problem(message="Problem to add a load to", keywords=True)
    if name is None:
        return
    problem = session.problems[name]

    option = choose("Loads", ["Add", "Remove"], default="Add")
    if option is None:
        return

    # `add_load` / `remove_load` mutate the problem before reporting back, so the
    # baseline has to be taken here rather than behind the `changed` gate.
    session.ensure_baseline()

    if option == "Add":
        values = ask_load(problem)
        if values is None:
            return
        changed = add_load(session, model, problem, values)
    else:
        changed = remove_load(problem)

    if not changed:
        return

    session.save_problems()
    session.draw_problem_conditions(name, model)
    session.record(f"{name}: {option.lower()} load")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
