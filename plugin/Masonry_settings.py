#! python3

import compas_masonry.settings
from compas_rui.forms import SettingsForm
from compas_session.namedsession import NamedSession


def RunCommand(is_interactive):

    session = NamedSession(name="COMPAS-Masonry")

    settingsform = SettingsForm(settings=compas_masonry.settings.SETTINGS, use_tab=True)
    if settingsform.show():
        pass

    if compas_masonry.settings.SETTINGS["Session"]["autosave.events"]:
        session.record(eventname="Update Settings")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand(True)
