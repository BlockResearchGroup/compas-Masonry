#! python3
# venv: masonry
# r: compas>=2.4, compas_assembly, compas_model, compas_rui>=0.2, compas_session>=0.2

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
