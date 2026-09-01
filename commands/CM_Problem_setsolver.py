#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Problem_solver_options — select and configure the solver on a Problem.

The solver *and* its parameters are one window: cycling the Solver option swaps
the visible parameter set, so the whole configuration is a single command line.

A problem holds ONE solver; selecting a new one replaces it. Running it is a
separate step (Problem_solve).

Solvers offered: CRA and RBE (rigid block equilibrium, via compas_cra),
LMGC90 (contact dynamics), and 3DEC through compas_3dec and an external,
licensed Itasca 3DEC installation.

- CRA / RBE are the ones installed in the Rhino environment. They return
  contact forces and NO displacements, so Results_show draws them as forces.
- LMGC90 needs `compas_lmgc90`, which has shipped a cp39 wheel since 0.1.10 and
  is installed in the Rhino environment. The option stays visible even where it
  is missing, and says so instead of raising an ImportError deep in the solve.
- 3DEC discovers the executable automatically when no explicit path is set.
  The Python adapter must be installed in the active environment.
- PRD and BLA are dropped from the picker (still in compas_dem: build a
  `Solver.PRD(...)` from a script if you want them).

Not exposed, deliberately:
- `d_bnd` / `eps` (CRA): the virtual displacement bound and contact overlap
  parameter. compas_dem loosened its defaults to 0.01 / 0.001 because tighter
  values report `infeasible` on finely discretised models. If a CRA solve comes
  back infeasible, `d_bnd` is the first knob to try — from a script for now.
- `mu`: neither `Solver.CRA` nor `Solver.RBE` takes it; both fall back to the
  contact law set by Problem_contactlaw, which is where it belongs.
- `theta`, `dt`, `contact_law` (LMGC90): compas_dem defaults. `lmgc90_solve`
  wants exactly two of duration/n_steps/dt, so only two are asked for.
"""

import pathlib

from compas_dem.models import BlockModel
from compas_dem.problem import Solver
from compas_masonry.inputs import Options
from compas_masonry.session import MasonrySession as Session
from compas_masonry.solvers import threedec_blocker
from compas_rui.feedback import warn

SOLVERS = ["CRA", "RBE", "LMGC90", "3DEC"]


def lmgc90_available() -> bool:
    """True if the LMGC90 backend can actually be imported.

    compas_lmgc90 is a compiled (Fortran + nanobind) extension. It has shipped a
    cp39 wheel since 0.1.10, so this is normally True inside Rhino — the earlier
    note here, that the build was cp312 and therefore unavailable, is obsolete.
    It stays a runtime check because the wheel is still platform-specific and a
    given environment may simply not have it.
    """
    try:
        import compas_lmgc90  # type: ignore # noqa: F401

        return True
    except Exception:
        return False


def make_threedec_solver(values):
    """Build a portable 3DEC solver configuration from command values."""
    timeout = float(values["timeout"])
    return Solver.ThreeDEC(
        version=values["version"],
        executable=values["executable"].strip() or None,
        workspace=values["workspace"].strip() or None,
        ratio=float(values["ratio"]),
        gravity_steps=int(values["gravity_steps"]),
        suppress_output=values["suppress_output"] == "Quiet",
        timeout=timeout if timeout > 0.0 else None,
    )


def ensure_threedec_gravity(problem):
    """Preserve Masonry's implicit self-weight convention for 3DEC."""
    if problem.boundary_conditions:
        return None
    gravity = problem.add_boundary_condition("Gravity")
    gravity.add_gravity()
    return gravity


def get_solver():
    """Ask for the solver and its parameters in a single prompt."""

    def is_(*kinds):
        return lambda v: v["solver"] in kinds

    options = Options("Solver")
    options.add_list("solver", SOLVERS, keyword="Solver")

    # CRA only: plain CRA or the penalty formulation
    options.add_toggle("penalty", False, off="Plain", on="Penalty", text=True, keyword="Formulation", visible=is_("CRA"))

    # LMGC90: exactly two of duration / n_steps / dt — dt is left computed
    options.add_number("duration", 1.0, minimum=0.0, keyword="Duration", units="s", prompt="Duration", visible=is_("LMGC90"))
    options.add_integer("n_steps", 100, minimum=1, keyword="Steps", prompt="Number of steps", visible=is_("LMGC90"))

    # 3DEC discovers the executable automatically when the path is empty.
    options.add_list("version", ["7.0", "9.0"], keyword="Version", visible=is_("3DEC"))
    options.add_text("executable", "", keyword="Executable", prompt="3DEC executable path", visible=is_("3DEC"))
    options.add_text("workspace", "", keyword="Workspace", prompt="3DEC runs directory", visible=is_("3DEC"))
    options.add_number("ratio", 1e-5, minimum=1e-12, keyword="Ratio", visible=is_("3DEC"))
    options.add_integer("gravity_steps", 10, minimum=1, keyword="GravitySteps", visible=is_("3DEC"))
    options.add_number("timeout", 0.0, minimum=0.0, keyword="Timeout", units="s", visible=is_("3DEC"))
    options.add_toggle("suppress_output", True, off="Terminal", on="Quiet", text=True, keyword="Output", visible=is_("3DEC"))

    # An `Output: Quiet|Verbose` toggle lived here and was removed on 2026-08-20.
    # It only ever fed the CRA/RBE `verbose` argument, whose backends print solver
    # iterations into the Rhino command line — noise in a plugin, and both
    # `Solver.CRA` and `Solver.RBE` already default it to False. Neither is passed
    # `verbose` any more.
    options.add_toggle("timer", False, off="NoTiming", on="Timing", text=True, keyword="Timer", visible=is_("CRA", "RBE"))

    values = options.get()
    if values is None:
        return None

    kind = values["solver"]
    timer = values["timer"] == "Timing"

    if kind == "CRA":
        return Solver.CRA(penalty=values["penalty"] == "Penalty", timer=timer)

    if kind == "RBE":
        return Solver.RBE(timer=timer)

    if kind == "3DEC":
        blocker = threedec_blocker(values["version"], values["executable"].strip())
        if blocker:
            warn(blocker)
            print("The solver is still set, so the problem is ready for a machine that can run it.")
        return make_threedec_solver(values)

    if not lmgc90_available():
        warn("compas_lmgc90 is not importable here, so an LMGC90 solve would fail. It ships a cp39 wheel, so `pip install compas_lmgc90` should work in this environment.")
        print("The solver is still set, so the problem is ready for an environment that has it.")

    # `verbose` is NOT passed. For LMGC90 it is not a flag but a PRINT INTERVAL:
    # `lmgc90_solve` does `step % verbose == 0` (lmgc90.py:275), so a Quiet toggle
    # sent 0 and every LMGC90 solve died with ZeroDivisionError. `Solver.LMGC90`
    # defaults it to 1000, which prints roughly nothing on a normal run — so it is
    # left alone rather than translated from anything the command asks for.
    return Solver.LMGC90(duration=values["duration"], n_steps=values["n_steps"])


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        return warn("No existing BlockModel in session. Please create one first.")
    if not session.problems:
        return warn("No problem in session. Run Problem_create first.")

    name = session.choose_problem(message="Problem to set the solver on", keywords=True)
    if name is None:
        return
    problem = session.problems[name]

    solver = get_solver()
    if solver is None:
        return

    # after the last bail-out, before the first change — see Session_undo
    session.ensure_baseline()

    problem.set_solver(solver)
    if solver.name == "3DEC":
        gravity = ensure_threedec_gravity(problem)
        if gravity is not None:
            print("Added the Gravity boundary-condition group required by the 3DEC workflow.")
    session.save_problems()
    print(f"Solver set on {name}: {solver}")
    # `solver.name`, not `type(solver).__name__` — `Solver.CRA()` is a factory that
    # returns a plain Solver, so the class name is always "Solver". This label is
    # what undo prints, so it has to say which solver.
    session.record(f"{name}: solver {solver.name}")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
