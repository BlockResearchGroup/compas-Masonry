#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Session_clear — empty the session and the document of everything the plugin drew.

Clearing used to leave most of it behind: four session keys were deleted and
`scene.clear()` was called, so problems, boundary conditions and results
survived as session state, and every layer under "Masonry" survived in the
document along with its geometry.

`session.clear_all()` clears the whole "Masonry" layer tree (children included,
which also sweeps orphans left by an earlier crash), deletes those layers, and
drops every session key the plugin owns.
"""

import pathlib

from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import confirm


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    if not confirm("Clear the current session? This deletes the model, every problem, and all results."):
        return

    session["params"] = {}
    session.clear_all()

    # History goes with it. Records pointing at a model that has just been deleted
    # are worse than no history: undo would restore a model the user cleared on
    # purpose, into a document that no longer has its layers.
    session.clear_history()

    print("Session cleared: model, problems, boundary conditions, results, and every Masonry layer.")
    print("Undo history cleared too — a cleared session cannot be undone.")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
