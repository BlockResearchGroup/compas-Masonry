#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Session_redraw — redraw the scene, or report what the session holds.

Status lives here rather than in a command of its own because it answers the
question a redraw provokes. Nothing in the plugin ever reported state: how many
problems exist, what each carries, whether a solve is stored and where undo
stands were only ever visible by running a command that happened to print them.

It is shown twice on purpose — printed to the command line, where it can be
scrolled back to and copied, and in an InfoForm, which survives the next command
writing over the command history.
"""

import pathlib

from compas_masonry.inputs import choose
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import confirm
from compas_rui.forms import InfoForm


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    option = choose("Session_redraw", ["Redraw", "Status"], default="Redraw")
    if option is None:
        return

    if option == "Status":
        summary = session.summary()
        print(summary)
        InfoForm(summary, title="COMPAS-Masonry — session status").show()
        return

    if not confirm("Redraw the current scene?"):
        return

    # `redraw_document()`, not `redraw()`: the latter only refreshes the block
    # scene objects, so reopening Rhino after an unsaved close left every layer
    # a command had created — problems, boundary conditions, results — missing,
    # and only Session_undo brought them back.
    session.redraw_document()


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
