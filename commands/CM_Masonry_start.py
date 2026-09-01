#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

import pathlib

import Rhino  # type: ignore
import System  # type: ignore

from compas_masonry.session import MasonrySession as Session
from compas_masonry.splash import SplashForm

pluginfile = Rhino.PlugIns.PlugIn.PathFromId(System.Guid("4384e04f-2997-429b-b3fc-53e7fe78703e"))
shared = pathlib.Path(str(pluginfile)).parent / "shared"


def RunCommand():
    Session.delete_instance()
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    print(session.basedir)

    form = SplashForm(title="COMPAS Masonry", url=str(shared / "index.html"))
    form.show()


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
