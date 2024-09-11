#! python3

import rhinoscriptsyntax as rs  # type: ignore

from compas_session.namedsession import NamedSession


def RunCommand(is_interactive):

    session = NamedSession(name="COMPAS-Masonry")

    scene = session.scene()

    # =============================================================================
    # Remove existing model
    # =============================================================================

    # =============================================================================
    # Make new model
    # =============================================================================

    options = ["RhinoBreps", "RhinoMeshes", "MeshGrid", "JSON", "OBJ"]
    option = rs.GetString("Make a Masonry Model", strings=options)
    if not option:
        return

    if option == "RhinoBreps":
        pass

    elif option == "RhinoMeshes":
        pass

    else:
        raise NotImplementedError

    # =============================================================================
    # Update scene
    # =============================================================================

    # =============================================================================
    # Save session
    # =============================================================================


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand(True)
