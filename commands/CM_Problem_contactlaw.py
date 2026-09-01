#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Problem_contactlaw_options — set the contact law and/or joint model on a Problem.

Renamed from Problem_contactmodel per the dev notes ("contact law" is the term
used in the Problem API: one problem = one solver, one contact law).

- **One window, both halves.** The contact law and the joint model used to be
  two branches of a ContactLaw/JointModel prompt, so setting both meant running
  the command twice. They are one `ContactProperties` object on the problem, and
  now one prompt. The friction parameter collapses to phi or mu depending on the
  FrictionInput toggle.
- Every field is seeded from what the problem already carries, because accept
  writes BOTH halves — fixed defaults would reset the joint model for anyone who
  came in only to change the friction angle.
- Single selection: a problem holds ONE contact law and ONE joint model at a
  time (setting a new one overwrites the old). Want a different contact law?
  Duplicate the problem.
- No Rhino geometry: contact properties aren't spatial.
"""

import pathlib

from compas_dem.models import BlockModel
from compas_masonry.inputs import Options
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import warn


def current(problem):
    """The contact law and joint model already on the problem, as field defaults.

    Seeding the window from what is stored is what makes ONE window safe. Both
    halves are written on accept, so fixed defaults would silently reset the
    joint model every time someone came in to nudge the friction angle. Seeded,
    accepting without editing writes back exactly what was there.
    """
    law = problem.contact_properties.contact_model
    joint = problem.contact_properties.joint_model
    return {
        "phi": 35.0 if law is None or law.phi is None else law.phi,
        "mu": 0.7 if law is None or law.mu is None else law.mu,
        "c": 0.0 if law is None or law.c is None else law.c,
        "t_c": 0.0 if law is None or law.t_c is None else law.t_c,
        "kn": 100e9 if joint is None or joint.kn is None else joint.kn,
        "kt": 70e9 if joint is None or joint.kt is None else joint.kt,
    }


def set_contact_properties(problem):
    """Ask for the contact law AND the joint model in one window."""
    seed = current(problem)

    options = Options("Contact law (MohrCoulomb) and joint model")
    options.add_toggle("friction", False, off="Phi", on="Mu", text=True, keyword="FrictionInput")
    options.add_number("phi", seed["phi"], minimum=0.0, maximum=90.0, keyword="Phi", units="deg", prompt="Friction angle phi", visible=lambda v: v["friction"] == "Phi")
    options.add_number("mu", seed["mu"], minimum=0.0, keyword="Mu", prompt="Friction coefficient mu", visible=lambda v: v["friction"] == "Mu")
    options.add_number("c", seed["c"], minimum=0.0, keyword="Cohesion", units="Pa", prompt="Cohesion c (0 = none)")
    options.add_number("t_c", seed["t_c"], minimum=0.0, keyword="TensileCutoff", units="Pa", prompt="Tensile cutoff t_c (0 = none)")
    options.add_number("kn", seed["kn"], minimum=0.0, keyword="NormalStiffness", units="Pa", prompt="Normal joint stiffness kn")
    options.add_number("kt", seed["kt"], minimum=0.0, keyword="TangentialStiffness", units="Pa", prompt="Shear joint stiffness kt")

    values = options.get()
    if values is None:
        return False

    kwargs = {"c": values["c"] or None, "t_c": values["t_c"] or None}
    if values["friction"] == "Mu":
        kwargs["mu"] = values["mu"]
    else:
        kwargs["phi"] = values["phi"]

    problem.set_contact_model("MohrCoulomb", **kwargs)
    problem.set_joint_model(values["kn"], values["kt"])

    # Read back from the stored model rather than echoing the input: phi and mu
    # are two views of the same thing (mu = tan(phi)), and MohrCoulomb derives
    # whichever was not given. Printing only what was typed hid the other one —
    # and mu is what the solvers actually use.
    law = problem.contact_properties.contact_model
    joint = problem.contact_properties.joint_model
    print(f"Contact law set: MohrCoulomb  phi = {law.phi:.3f} deg  mu = {law.mu:.4f}  c = {law.c}  t_c = {law.t_c}")
    print(f"Joint model set: kn = {joint.kn}  kt = {joint.kt}")
    return True


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        return warn("No existing BlockModel in session. Please create one first.")
    if not session.problems:
        return warn("No problem in session. Run Problem_create first.")

    name = session.choose_problem(message="Problem to set the contact law on", keywords=True)
    if name is None:
        return
    problem = session.problems[name]

    # `set_contact_properties` prompts and may be cancelled, so this can fire for
    # a command that changes nothing — at most one extra snapshot per session,
    # since `ensure_baseline` is a no-op after the first.
    session.ensure_baseline()

    if not set_contact_properties(problem):
        return

    session.save_problems()
    session.record(f"{name}: contact properties")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
