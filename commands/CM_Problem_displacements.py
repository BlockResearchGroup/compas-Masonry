#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Problem_displacements — prescribed displacements and rotations on a Problem.

Same shape as Problem_loads: a prescribed movement is a typed object
(`Translation`, `Rotation`) held by a `BoundaryConditionGroup`, and the group is
chosen in the same window as the movement — extend an existing one, or New. Each
group gets one layer under "…::BoundaryConditions::<group>".

**Only DISPLACEMENT groups are offered here**, and Problem_loads offers only the
load ones. See Problem_loads' docstring for what that split is and is not.

`Translation` takes dx/dy/dz **per component**, where `None` means "this DOF is
unconstrained" — which is not the same as prescribing 0.0. The window mirrors
that: a Constrain toggle per axis, and an axis's value appears only when that
axis is constrained.

`Rotation` does NOT work that way: it takes one rotation vector, and
`add_rotation` has no per-component None. An axis left free here is written as
0.0, so a rotation prescribes all three components whether you set them or not.
The toggles are kept for symmetry of the window, but that is what they mean.

Visualization: NO displaced copy of the geometry. A prescribed translation is an
arrow, a prescribed rotation a circle around its axis. Results_show is what draws
displaced geometry.

**Fixed supports are not edited here.** They live on the model
(Model_supports -> `Block.is_support`) and the solvers read them from there.

**CRA and RBE cannot apply prescribed movements.** They solve for the
displacements of the free blocks; support blocks are excluded from the
equilibrium system entirely and have no displacement degrees of freedom, so a
settlement cannot be expressed. That is structural, not a missing feature. Those
are LMGC90 / PRD / BLA only — and none of those is installed in Rhino yet. This
command builds the movement anyway (an LMGC90 build is in the pipeline) and warns
when the problem's solver cannot apply it.
"""

import pathlib

import rhinoscriptsyntax as rs  # type: ignore

import compas_rhino.objects
from compas_dem.models import BlockModel
from compas_masonry.boundaryconditions import describe
from compas_masonry.boundaryconditions import group_names
from compas_masonry.boundaryconditions import groups_of_kind
from compas_masonry.boundaryconditions import next_group_name
from compas_masonry.boundaryconditions import remove_condition
from compas_masonry.boundaryconditions import remove_group
from compas_masonry.inputs import Options
from compas_masonry.inputs import choose
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import warn

NEW = "New"

# Solvers that can apply a prescribed movement. CRA/RBE cannot — see the module
# docstring — and compas_dem raises rather than silently ignoring one.
DISPLACEMENT_SOLVERS = ("LMGC90", "PRD", "BLA", "3DEC")


def selected_nodes(session, model, message):
    guids = compas_rhino.objects.select_objects(message=message)
    if not guids:
        return []
    guid_element_map = session.guid_element_map(model)
    return sorted({n for n in (session.find_node(g, guid_element_map) for g in guids) if n is not None})


def warn_if_solver_cannot_apply(problem, movement_kind=None) -> None:
    """Say up front if this problem's solver will refuse the movement.

    Better here than at solve time: the user is about to spend effort defining
    something the configured solver cannot use.
    """
    solver = Session.solver_of(problem)
    name = getattr(solver, "name", None)
    if name is None:
        print("No solver set yet. Note that CRA and RBE cannot apply prescribed movements — use LMGC90, PRD or BLA.")
        return
    if name == "3DEC" and movement_kind == "Rotation":
        warn("3DEC supports prescribed translations, but prescribed rotations are not yet supported by the compas_3dec adapter.")
        return
    if name not in DISPLACEMENT_SOLVERS:
        warn(f"{name} applies no boundary conditions at all: it solves self-weight equilibrium and never reads them.")
        print(f"  The movement will be stored, but Problem_solve REFUSES to run {name} on a problem that carries one —")
        print("  otherwise it would return a self-weight answer that silently ignored it.")
        print(f"  Applying one needs {', '.join(DISPLACEMENT_SOLVERS)} — set it in Problem_setsolver.")


def ask_movement(problem):
    """Ask for the group and every movement field in one window."""

    def is_translation(v):
        return v["kind"] == "Translation"

    def is_rotation(v):
        return v["kind"] == "Rotation"

    def constrained(axis, rotational=False):
        test = is_rotation if rotational else is_translation
        return lambda v: test(v) and v[f"use_{axis}"]

    existing = group_names(problem, "displacement")

    options = Options("Prescribed movement")
    options.add_list("group", [NEW] + existing, keyword="Group")
    options.add_text("newgroup", next_group_name(problem, "displacement"), keyword="Name", visible=lambda v: v["group"] == NEW)

    options.add_list("kind", ["Translation", "Rotation"], keyword="Type")

    # per component: unconstrained (None) is not the same as a prescribed 0.0
    for axis in ("x", "y", "z"):
        options.add_toggle(f"use_{axis}", True, off="Free", on="Fixed", text=False, keyword=f"Constrain{axis.upper()}", visible=is_translation)
        options.add_number(f"d{axis}", 0.0, keyword=f"D{axis.upper()}", units="m", prompt=f"Prescribed d{axis}", visible=constrained(axis))

    for axis in ("x", "y", "z"):
        options.add_toggle(f"use_r{axis}", True, off="Free", on="Fixed", text=False, keyword=f"ConstrainR{axis.upper()}", visible=is_rotation)
        options.add_number(f"r{axis}", 0.0, keyword=f"R{axis.upper()}", units="rad", prompt=f"Prescribed r{axis}", visible=constrained(f"r{axis}", rotational=True))

    values = options.get()
    if values is None:
        return None

    # `group` stays the SELECTOR (NEW, or an existing group's name); `newgroup`
    # carries the normalized name. See the same spot in CM_Problem_loads.
    if values["group"] == NEW:
        name = values["newgroup"].strip()
        if not name:
            warn("A movement group needs a name.")
            return None
        values["newgroup"] = name
    return values


def resolve_group(problem, values):
    """The BoundaryConditionGroup to write into: an existing one, or a new one.

    Called after the block selection, never before: `add_boundary_condition`
    registers the group straight away, so creating it first and then cancelling
    the selection would leave an empty group holding the name.
    """
    name = values["group"]

    if name != NEW:
        for group in groups_of_kind(problem, "displacement"):
            if group.name == name:
                return group
        warn(f"Movement group [{name}] is no longer on this problem.")
        return None

    try:
        return problem.add_boundary_condition(values["newgroup"])
    except ValueError as e:
        # names are unique across the whole problem, load groups included
        warn(str(e))
        return None


def add_movement(session, model, problem, values):
    nodes = selected_nodes(session, model, "Select blocks to prescribe a movement on")
    if not nodes:
        return False

    if values["kind"] == "Translation":
        # None where the axis is unconstrained — never 0.0, which would prescribe
        # a movement of exactly zero and pin the block. `add_displacement` passes
        # the list straight through as dx/dy/dz, so the Nones survive.
        components = {axis: (values[f"d{axis}"] if values[f"use_{axis}"] else None) for axis in ("x", "y", "z")}
        if all(v is None for v in components.values()):
            warn("Every axis is free, so there is nothing to prescribe.")
            return False
        displacement = [components["x"], components["y"], components["z"]]
        if not any(value for value in displacement if value is not None):
            warn("The prescribed translation is zero, so no displacement or arrow would be produced.")
            return False
        group = resolve_group(problem, values)
        if group is None:
            return False
        for node in nodes:
            problem.add_displacement(block_index=node, displacement=displacement, boundary_condition=group)
        print(f"Added a prescribed translation on {len(nodes)} block(s) to [{group.name}].")
    else:
        components = {axis: (values[f"r{axis}"] if values[f"use_r{axis}"] else None) for axis in ("x", "y", "z")}
        if all(v is None for v in components.values()):
            warn("Every axis is free, so there is nothing to prescribe.")
            return False
        group = resolve_group(problem, values)
        if group is None:
            return False
        # `Rotation` takes one vector rather than per-component values, and
        # `add_rotation` does not accept None — an unconstrained axis is 0.0 here
        rotation = [0.0 if components[axis] is None else components[axis] for axis in ("x", "y", "z")]
        for node in nodes:
            problem.add_rotation(block_index=node, rotation=rotation, boundary_condition=group)
        print(f"Added a prescribed rotation on {len(nodes)} block(s) to [{group.name}].")

    warn_if_solver_cannot_apply(problem, values["kind"])
    return True


def remove_movement(problem):
    """Remove movements, one at a time or a whole group at once.

    Same rule as Problem_loads: removing a group removes the group object and
    frees its name; removing one movement leaves the group standing.
    """
    groups = groups_of_kind(problem, "displacement")
    if not groups:
        warn("This problem carries no prescribed movements.")
        return False

    scope = choose("Remove", ["One", "Group"], default="One")
    if scope is None:
        return False

    names = [group.name for group in groups]

    if scope == "Group":
        name = names[0] if len(names) == 1 else rs.ListBox(names, message="Movement group to remove", title="Displacements")
        if not name:
            return False
        group = groups[names.index(name)]
        count = len(group.displacements)
        remove_group(problem, group)
        print(f"Removed group [{name}] and the {count} prescribed movement(s) in it.")
        return True

    entries = [(group, bc) for group in groups for bc in group.displacements]
    if not entries:
        warn("This problem carries no prescribed movements.")
        return False

    labels = [f"{i}: [{group.name}] {describe(bc)}" for i, (group, bc) in enumerate(entries)]
    label = rs.ListBox(labels, message="Prescribed movement to remove", title="Displacements")
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

    name = session.choose_problem(message="Problem to prescribe a movement on", keywords=True)
    if name is None:
        return
    problem = session.problems[name]

    option = choose("Prescribed movements", ["Add", "Remove"], default="Add")
    if option is None:
        return

    # `add_movement` / `remove_movement` mutate the problem before reporting back,
    # so the baseline has to be taken here rather than behind the `changed` gate.
    session.ensure_baseline()

    if option == "Add":
        values = ask_movement(problem)
        if values is None:
            return
        changed = add_movement(session, model, problem, values)
    else:
        changed = remove_movement(problem)

    if not changed:
        return

    session.save_problems()
    session.draw_problem_conditions(name, model)
    session.record(f"{name}: {option.lower()} prescribed movement")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
