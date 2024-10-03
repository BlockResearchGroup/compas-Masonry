#! python3
# venv: masonry
# r: compas>=2.4, compas_assembly, compas_model, compas_rui>=0.2, compas_session>=0.2

from compas_rui.forms import FileForm
from compas_session.namedsession import NamedSession


def RunCommand(is_interactive):

    session = NamedSession(name="COMPAS-Masonry")

    filepath = FileForm.save(session.basedir, "COMPAS-Masonry.json")
    if not filepath:
        return

    session.save(filepath)


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand(True)
