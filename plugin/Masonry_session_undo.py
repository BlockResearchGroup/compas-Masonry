#! python3

import rhinoscriptsyntax as rs  # type: ignore

from compas_session.namedsession import NamedSession


def RunCommand(is_interactive):

    session = NamedSession(name="COMPAS-Masonry")

    scene = session.scene()

    if session.undo():
        scene.clear()
        scene = session.scene()

        rs.EnableRedraw(False)
        scene.draw()
        rs.EnableRedraw(True)
        rs.Redraw()


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand(True)