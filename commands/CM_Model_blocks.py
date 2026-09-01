#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Model_blocks_options — RhinoCommon variant of Model_blocks.

Every template parameter is shown at once as a command line option, so an arch
is defined in a single prompt (rise / span / thickness / depth / blocks) instead
of five sequential questions.
"""

import pathlib

import rhinoscriptsyntax as rs  # type: ignore

from compas_dem.models import BlockModel
from compas_dem.templates import ArchTemplate
from compas_dem.templates import BarrelVaultTemplate
from compas_dem.templates import DomeTemplate
from compas_masonry.inputs import Options
from compas_masonry.inputs import choose
from compas_masonry.session import MasonrySession as Session


def get_arch():
    options = Options("Arch")
    options.add_number("rise", 3.0, minimum=0.0, keyword="Rise")
    options.add_number("span", 6.0, minimum=0.0, keyword="Span")
    options.add_number("thickness", 0.5, minimum=0.0, keyword="Thickness")
    options.add_number("depth", 0.5, minimum=0.0, keyword="Depth")
    options.add_integer("n", 15, minimum=3, keyword="Blocks", prompt="Number of blocks")

    values = options.get()
    if values is None:
        return None

    template = ArchTemplate(**values)
    return BlockModel.from_template(template)


def get_dome():
    options = Options("Dome")
    options.add_integer("meridians", 20, minimum=3, keyword="Meridians")
    options.add_integer("hoops", 10, minimum=3, keyword="Hoops")
    options.add_number("oculus", 3.14 / 30, minimum=0.0, keyword="OculusAngle", units="rad", prompt="Oculus angle")
    options.add_number("spring", 3.14 / 2, minimum=0.0, keyword="SpringingAngle", units="rad", prompt="Springing angle")
    # r_i/R_i and r_f/R_f would collapse to the same keyword, hence the explicit ones.
    options.add_number("r_i", 3.9, minimum=0.0, keyword="InnerRadiusSpringing")
    options.add_number("r_f", 3.2, minimum=0.0, keyword="InnerRadiusOculus")
    options.add_number("R_i", 4.0, minimum=0.0, keyword="OuterRadiusSpringing")
    options.add_number("R_f", 3.5, minimum=0.0, keyword="OuterRadiusOculus")

    values = options.get()
    if values is None:
        return None

    template = DomeTemplate(**values)
    return BlockModel.from_template(template)


def get_barrelvault():
    options = Options("BarrelVault")
    options.add_number("span", 6.0, minimum=0.0, keyword="Span")
    options.add_number("length", 6.0, minimum=0.0, keyword="Length")
    options.add_number("rise", 3.0, minimum=0.0, keyword="Rise")
    options.add_number("thickness", 0.5, minimum=0.0, keyword="Thickness")
    options.add_integer("vou_span", 20, minimum=3, keyword="SpanBlocks", prompt="Number of span blocks")
    options.add_integer("vou_length", 20, minimum=3, keyword="LengthBlocks", prompt="Number of length blocks")

    values = options.get()
    if values is None:
        return None

    template = BarrelVaultTemplate(**values)
    return BlockModel.from_barrelvault(template)


def get_json():
    options = Options("Json")
    options.add_text("path", str(pathlib.Path().home() / "blockmodel.json"), keyword="Path", prompt="Path to JSON file")

    values = options.get()
    if values is None or not values["path"]:
        return None

    return BlockModel.from_json(values["path"])


# =============================================================================
# Command
# =============================================================================


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    # Before `clear_model`, not after: that call is already a change, and it runs
    # before the user has picked anything, so a baseline taken later would make
    # the clear itself un-undoable.
    session.ensure_baseline()

    session.clear_model()

    option = choose("BlockModel", ["Arch", "Dome", "BarrelVault", "RhinoMeshes", "RhinoPolysurfaces", "Json"])
    if option is None:
        return

    model = None

    if option == "Arch":
        model = get_arch()

    elif option == "Dome":
        model = get_dome()

    elif option == "BarrelVault":
        model = get_barrelvault()

    elif option == "RhinoMeshes":
        guids = rs.GetObjects("Select meshes", rs.filter.mesh)
        if not guids:
            return
        model = BlockModel.from_rhinomeshes(guids)

    elif option == "RhinoPolysurfaces":
        guids = rs.GetObjects("Select closed polysurfaces", rs.filter.polysurface)
        if not guids:
            return
        model = BlockModel.from_polysurfaces(guids)

    elif option == "Json":
        model = get_json()

    # =============================================================================
    # Session update - add model to session and scene
    # =============================================================================

    if not model:
        return

    session.set_model(model)

    rs.Redraw()
    session.record(f"BlockModel: {option}")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
