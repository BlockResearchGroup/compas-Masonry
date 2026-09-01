#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Problem_solve — solve a Problem.

**Every boundary condition group on the problem is solved.** There is no
selection: `problem.solve()` takes no arguments and applies every group it
carries. A different set of loads means a different problem — duplicate it in
Problem_create. For 3DEC, this command exposes `Problem.set_solve_order()` and
each group is executed as a sequential stage after gravity.

Solving draws NOTHING. One `Results` per solve is stored on the session under a
key naming the solver and the time it ran ("RBE_2026-08-04T15-30-12"), so a
re-solve after changing a material or a contact law never overwrites the earlier
run and the two can be compared. Results_show is what puts geometry in the
document.

Three things about the environment shape this command, all verified rather than
assumed:

1. **No external solver executable is needed for CRA/RBE.** compas_cra 0.8.0
   runs IPOPT in-process through `compas_cra._native`; the pyomo model and its
   `SolverFactory("ipopt")` PATH lookup are gone, and with them the PATH
   workaround this command used to run first.
2. **CRA and RBE ignore boundary conditions entirely.** `cra_solve` and
   `rbe_solve` take the problem, the model, a friction coefficient and a density
   — and never read `problem.boundary_conditions`. They solve self-weight
   equilibrium. So a problem carrying loads or prescribed movements does not
   fail under CRA: it returns a **self-weight answer that looks like a result**,
   which is worse. Refused here, because nothing downstream will.
3. CRA/RBE dereference `block.material.density`, and need a contact law for the
   friction coefficient. Both are checked so a failure names the fix.

`Results` is a compas Data, so it serializes onto the session as is.
"""

import pathlib
import time

import rhinoscriptsyntax as rs  # type: ignore

from compas_dem.models import BlockModel
from compas_masonry.boundaryconditions import conditions_of
from compas_masonry.boundaryconditions import loads_of
from compas_masonry.inputs import choose
from compas_masonry.results import tension_report
from compas_masonry.session import MasonrySession as Session
from compas_masonry.solvers import threedec_blocker
from compas_rui.feedback import warn


def result_key(solver_name) -> str:
    """Key a result set by its solver and when it ran: "RBE_2026-08-04T15-30-12".

    A problem is the load case, so there are no BC names left to key by. The
    timestamp means a re-solve after changing a material or a contact law is kept
    beside the earlier run rather than overwriting it — colons are avoided because
    the key becomes a Rhino layer name.
    """
    return f"{solver_name}_{time.strftime('%Y-%m-%dT%H-%M-%S')}"


# `cra_accepts_loads()` lived here and was deleted on 2026-08-07. It inspected
# `compas_cra.equilibrium.cra_solve` for a `loads=` parameter, because compas_dem
# used to pass one and the released compas_cra would raise a TypeError mid-solve.
# compas_dem no longer passes loads to CRA at all — `cra_solve` takes the problem,
# the model, mu and density and reads no boundary conditions — so there is nothing
# to be compatible with. What replaced it is the guard below, which refuses the
# solve outright rather than checking whether it would crash.


def store(session, problem_name, key, results) -> None:
    """Persist one Results on the session, keyed by problem and result key."""
    stored = session.setdefault("results", dict)
    problem_results = stored.setdefault(problem_name, {})
    problem_results[key] = results
    session["results"] = stored


def check_ready(model, problem, name):
    """Return the first unmet precondition for solving, or None if ready."""
    if model.graph.number_of_edges() == 0:
        return "No contacts in the model. Run Model_contacts first — every solver works off the contact interfaces."

    if Session.solver_of(problem) is None:
        return f"{name} has no solver. Run Problem_setsolver first."

    if not problem.contact_properties.contact_model:
        return f"{name} has no contact law. Run Problem_contactlaw first — check_model_validity requires one."

    # supports live on the model only — a problem never carries a copy
    if not any(block.is_support for block in model.elements()):
        return "The model has no supports. Run Model_supports first."

    solver_name = Session.solver_of(problem).name

    # 3DEC is the one backend that shells out to external licensed software.
    # Configuring it anywhere is fine and deliberate -- the parameters are
    # portable -- but refuse to START a run that cannot reach an executable,
    # rather than let it fail inside a subprocess launch after the stage
    # prompts. Asked of compas_3dec, not of sys.platform: see threedec_blocker.
    if solver_name == "3DEC":
        parameters = Session.solver_of(problem).parameters
        blocker = threedec_blocker(parameters.get("version"), parameters.get("executable") or "")
        if blocker:
            return blocker

    # CRA/RBE read no boundary conditions at all — they solve self-weight
    # equilibrium — so a problem carrying any would come back with a plausible
    # answer to a question nobody asked. Refuse instead of returning that.
    if solver_name in ("CRA", "RBE"):
        groups = problem.boundary_conditions
        conditions = sum(len(conditions_of(group)) for group in groups)
        if conditions:
            listed = ", ".join(group.name for group in groups)
            return (
                f"{name} carries {conditions} boundary condition(s) in [{listed}], and {solver_name} applies none of them — "
                f"it solves self-weight equilibrium only, so it would return a result that silently ignores them. "
                "Use LMGC90, or remove them in Problem_loads / Problem_displacements."
            )

    # CRA/RBE read block.material.density directly. compas_dem raises a clear
    # ValueError now, but naming the command to run is more useful than that.
    missing = [b.graphnode for b in model.elements() if b.material is None or b.material.density is None]
    if missing:
        shown = ", ".join(str(n) for n in missing[:5])
        more = f" (+{len(missing) - 5} more)" if len(missing) > 5 else ""
        return f"Blocks {shown}{more} have no material with a density. Run Model_material, then Model_materialassign."

    return None


def stamp_provenance(results, problem, solver) -> None:
    """Record on the Results WHAT produced them, so they stay readable later.

    A Results carries `model_id`, `problem_id` and the per-node/edge data, and
    nothing about the configuration that produced it. A problem is mutable: change
    the solver, the contact law or the loads and yesterday's results still sit
    under the same problem name, describing a setup that no longer exists
    anywhere. `problem_id` does not save you — edit a problem in place and the
    guid is unchanged while the configuration differs.

    `metadata` is the right place: it is in `Results.__data__`, restored by
    `__from_data__`, and so survives a session save and re-import.

    Everything stamped is a PRIMITIVE, deliberately. This is a record, not a live
    object: `contact_model.__data__` is a plain dict (it is also the only way to
    read `mu`, which is a property over `_mu` and not a public attribute), and
    storing the Data object instead would make an old result unloadable the day
    compas_dem renames the class.

    `setdefault` throughout, so a backend that starts writing its own values wins.
    """
    if results is None:
        return

    # WHICH backend. `results.tension_contacts` depends on this: 3DEC tension must
    # be read from native normal subcontact forces, because the affine vertex
    # values a 3DEC-to-DEM conversion produces carry negative weights that are not
    # tension. No compas_dem backend writes it, so before this stamp existed that
    # guard never fired and 3DEC tension was over-reported.
    if solver is not None:
        results.metadata.setdefault("solver", solver.name)
        results.metadata.setdefault("solver_parameters", dict(getattr(solver, "parameters", None) or {}))

    if problem is None:
        return

    results.metadata.setdefault("problem_name", problem.name)

    contact_model = getattr(problem.contact_properties, "contact_model", None)
    if contact_model is not None:
        try:
            results.metadata.setdefault("contact_model", dict(contact_model.__data__))
        except Exception:
            # a contact model that cannot describe itself is not worth failing a
            # solve over — the rest of the stamp is still useful
            results.metadata.setdefault("contact_model", {"name": type(contact_model).__name__})

    results.metadata.setdefault("boundary_conditions", [group.name for group in problem.boundary_conditions])


def solve(problem, progress_callback=None, event_pump=None):
    """Run the problem's solver over every boundary condition it carries.

    `problem.solve()` takes no arguments: solving moved onto Problem, and the
    subset selection is gone. The private-list swap that used to live here worked
    around `BlockModel.solve` assigning to a property with no setter — both the
    assignment and the property are gone.

    Returns the Results, or None on failure (reported through `warn`).
    """
    try:
        solver = Session.solver_of(problem)
        if solver is not None and solver.name == "3DEC" and (progress_callback is not None or event_pump is not None):
            results = problem.solve(
                progress_callback=progress_callback,
                event_pump=event_pump,
            )
        else:
            results = problem.solve()

        stamp_provenance(results, problem, solver)
        return results
    except ImportError as e:
        # the solver backends (compas_cra, compas_lmgc90, ...) are optional
        warn(f"The solver backend is not installed: {e}")
    except NotImplementedError as e:
        warn(f"The solver does not support this problem: {e}")
    except Exception as e:
        warn(f"Solve failed: {e}")
    return None


def rhino_progress_handlers():
    """Return concise 3DEC progress and Rhino UI-pump callbacks."""
    import Rhino  # type: ignore

    previous = [None]

    def progress(event):
        message = event.get("message")
        if not message or message == previous[0]:
            return
        previous[0] = message
        print(message, flush=True)
        try:
            Rhino.RhinoApp.SetCommandPrompt(message)
        except Exception:
            pass

    def pump():
        Rhino.RhinoApp.Wait()

    return progress, pump


def choose_threedec_solve_order(problem):
    """Choose the sequential 3DEC stage order, keeping gravity first.

    Returns the complete ordered list of group names, or ``None`` when the
    command is cancelled. With zero or one non-gravity group the mechanically
    valid order is unambiguous and no dialog is shown.
    """
    groups = list(problem.boundary_conditions)
    # BoundaryConditionGroup currently carries a default ``g`` value on every
    # group, including load-only groups. Masonry's explicit gravity stage is
    # therefore identified by the canonical name created by Problem_setsolver.
    gravity = [group for group in groups if group.name.strip().casefold() == "gravity"]
    remaining = [group for group in groups if group not in gravity]
    current = gravity + remaining
    if len(remaining) < 2:
        return [group.name for group in current]

    action = choose("3DEC analysis-stage order", ["Use current order", "Change order"], default="Use current order")
    if action is None:
        return None
    if action == "Use current order":
        return [group.name for group in current]

    ordered = list(gravity)
    available = list(remaining)
    position = len(ordered) + 1
    while len(available) > 1:
        names = [group.name for group in available]
        selected = rs.ListBox(names, message=f"Select analysis stage {position}", title="3DEC Analysis Order")
        if selected is None:
            return None
        group = next(group for group in available if group.name == selected)
        ordered.append(group)
        available.remove(group)
        position += 1
    ordered.extend(available)
    return [group.name for group in ordered]


def choose_threedec_stages(problem, solver):
    """Order and group 3DEC boundary conditions into DAT-file stages."""
    groups_by_name = {group.name: group for group in problem.boundary_conditions}
    saved = solver.parameters.get("stages")
    saved_names = [name for stage in (saved or []) for name in stage]
    if saved and len(saved_names) == len(groups_by_name) and set(saved_names) == set(groups_by_name):
        action = choose("3DEC execution plan", ["Use saved plan", "Edit plan"], default="Use saved plan")
        if action is None:
            return None
        if action == "Use saved plan":
            return [list(stage) for stage in saved]

    order = choose_threedec_solve_order(problem)
    if order is None:
        return None
    ordered = [groups_by_name[name] for name in order]
    load_groups = [group for group in ordered if loads_of(group) and not group.displacements]
    if len(load_groups) < 2:
        return [[group.name] for group in ordered]

    mode = choose(
        "3DEC load grouping",
        ["Combine consecutive loads", "Separate every load group", "Define phase breaks"],
        default="Combine consecutive loads",
    )
    if mode is None:
        return None

    stages = []
    for group in ordered:
        # Gravity and every prescribed-displacement group are hard phase
        # boundaries. A mixed group is kept alone; compas_3dec writes its load
        # part first and its displacement part as the following stage.
        is_gravity = group.name.strip().casefold() == "gravity"
        if is_gravity or group.displacements or not loads_of(group):
            stages.append([group.name])
            continue
        if mode == "Separate every load group" or not stages:
            stages.append([group.name])
            continue
        previous_group = groups_by_name[stages[-1][-1]]
        can_join = bool(loads_of(previous_group)) and not previous_group.displacements
        if mode == "Define phase breaks" and can_join:
            action = choose(
                "3DEC stage for {}".format(group.name),
                ["Continue current load phase", "Start new load phase"],
                default="Continue current load phase",
            )
            if action is None:
                return None
            can_join = action == "Continue current load phase"
        if can_join:
            stages[-1].append(group.name)
        else:
            stages.append([group.name])
    return stages


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        return warn("No existing BlockModel in session. Please create one first.")
    if not session.problems:
        return warn("No problem in session. Run Problem_create first.")

    name = session.choose_problem(message="Problem to solve", keywords=True)
    if name is None:
        return
    problem = session.problems[name]

    not_ready = check_ready(model, problem, name)
    if not_ready:
        return warn(not_ready)

    solver = Session.solver_of(problem)
    key = result_key(solver.name)

    if solver.name == "3DEC":
        stages = choose_threedec_stages(problem, solver)
        if stages is None:
            return
        session.ensure_baseline()
        solve_order = [group for stage in stages for group in stage]
        problem.set_solve_order(solve_order)
        solver.set_stages(stages)
        print("3DEC execution plan:")
        for index, stage in enumerate(stages, start=1):
            print("  {}. {}".format(index, " + ".join(stage)))

    # A CRA/RBE ipopt-on-PATH check lived here and was removed on 2026-08-31:
    # compas_cra 0.8.0 solves in-process and never looks up an executable, so
    # the check warned "this will fail" at installations that solve perfectly.

    groups = problem.boundary_conditions
    if groups:
        loads = sum(len(loads_of(group)) for group in groups)
        movements = sum(len(group.displacements) for group in groups)
        listed = ", ".join(group.name for group in groups)
        print(f"Solving {name} ({solver.name}) with {loads} load(s) and {movements} prescribed movement(s) in [{listed}].")
    else:
        print(f"Solving {name} ({solver.name}) under self-weight only.")

    # Right before the solve: everything above either bails out or only reads, and
    # a solve is the one action here that is expensive to repeat — so the state it
    # was launched from is worth being able to return to.
    session.ensure_baseline()

    started = time.time()
    if solver.name == "3DEC":
        progress_callback, event_pump = rhino_progress_handlers()
        results = solve(problem, progress_callback=progress_callback, event_pump=event_pump)
    else:
        results = solve(problem)
    if results is None:
        return
    elapsed = time.time() - started

    results.metadata["solver"] = solver.name
    results.metadata["solved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    results.metadata["duration_s"] = round(elapsed, 3)

    try:
        store(session, name, key, results)
    except Exception as e:
        return warn(f"Solved, but the result could not be stored on the session: {e}")

    print(f"Solved in {elapsed:.1f}s, stored on {name} as {key}.")

    # A solve that succeeds is not the same as a solve that is admissible: masonry
    # takes no tension, so a converged answer holding tensile contact corners is
    # still not one the structure can deliver. Said at the moment it is produced,
    # because nothing else here would report it and Results_show may never be run.
    reported = tension_report(results)
    if reported is not None:
        expected, message = reported
        if expected:
            print(message)
        else:
            warn(message)

    print("Next: Results_show to draw it (nothing is drawn by solving).")
    session.record(f"Solve {name}: {key}")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
