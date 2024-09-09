#! python3

import rhinoscriptsyntax as rs  # type: ignore

import compas_masonry.settings
from compas_session.namedsession import NamedSession


def RunCommand(is_interactive):

    session = NamedSession(name="COMPAS-Masonry")
    scene = session.scene()

    result = rs.MessageBox(
        "Note that this will remove all COMPAS Masonry data and objects. Do you wish to proceed?",
        buttons=4 | 32 | 256 | 0,
        title="Clear COMPAS Masonry",
    )

    if result == 6:
        scene.clear()

        if compas_masonry.settings.SETTINGS["Session"]["autosave.events"]:
            session.record(eventname="Clear")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand(True)
