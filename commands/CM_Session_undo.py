#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Session_undo — step one state back through the plugin's own history.

This is NOT Rhino's undo. Rhino's `_Undo` restores document geometry and knows
nothing about the session, so using it after a plugin command leaves the drawn
objects and the session state disagreeing. This restores the session — the
model, the problems and their boundary conditions, the results, the settings —
and redraws the document from it.

History is recorded by the commands that change something, keeps the last 10
states, and lives on disk in `~/.compas_session/COMPAS-Masonry.session/__records/`,
so it survives a Rhino restart.

Two limits worth knowing:

- **TNA is not covered.** The envelope and the form diagram are drawn inline by
  the TNA commands rather than through the session, so there is nothing for a
  restore to call. Their layers are left exactly as they are.
- **History is global, not per-document.** Every command roots the session at
  `~/.compas_session`, so undo in a freshly opened .3dm walks the history of
  whatever was worked on last.
"""

import pathlib

import rhinoscriptsyntax as rs  # type: ignore

from compas_masonry.session import MasonrySession as Session


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    # False means there was nothing to undo and NOTHING was touched — the session
    # prints why. Returning here matters: the document is only rebuilt when the
    # history actually moved.
    if not session.undo():
        return

    rs.Redraw()


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
