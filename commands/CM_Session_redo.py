#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Session_redo — step one state forward through the plugin's own history.

The mirror of Session_undo, and subject to the same limits (TNA is not covered;
history is global rather than per-document) — see that command for the detail.

Recording a new state discards everything ahead of the cursor, so a change made
after an undo makes redo unavailable. That is standard undo semantics and it is
`LazyLoadSession.record` that enforces it, not this command.
"""

import pathlib

import rhinoscriptsyntax as rs  # type: ignore

from compas_masonry.session import MasonrySession as Session


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    # False means there was nothing to redo and NOTHING was touched — the session
    # prints why. Returning here matters: the document is only rebuilt when the
    # history actually moved.
    if not session.redo():
        return

    rs.Redraw()


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
