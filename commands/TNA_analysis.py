#! python3
# venv: brg-csd
# r: compas_masonry

import ast

import rhinoscriptsyntax as rs  # type: ignore
from numpy import array
from numpy import zeros

from compas_masonry.scene import RhinoFormDiagramObject
from compas_masonry.session import MasonrySession as Session
from compas_rui import feedback
from compas_tna.diagrams import FormDiagram
from compas_tno.analysis import Analysis


def RunCommand():
    session = Session()

    formdiagram = session["formdiagram"]
    envelope = session["envelope"]

    if not formdiagram:
        feedback.warn("There is no FormDiagram")
        return

    if not envelope:
        feedback.warn("There is no Envelope")
        return

    formobject: RhinoFormDiagramObject = session.scene.find_by_itemtype(FormDiagram)  # type: ignore
    if not formobject:
        session.scene.add(formdiagram, name="FormDiagram", layer="Masonry::TNA::FormDiagram")  # type: ignore

    formobject.redraw()

    # =============================================================================
    # Create an analysis
    # =============================================================================

    objective = rs.GetString(
        message="Objective",
        strings=[
            "MinimumThrust",
            "MinimumThickness",
            "MaximumThrust",
            "MaximumLoad",
            "SupportDisplacement",
            "Bestfit",
        ],
    )
    if not objective:
        return

    if objective == "MinimumThrust":
        analysis = Analysis.create_minthrust_analysis(formdiagram, envelope)

    elif objective == "MinimumThickness":
        analysis = Analysis.create_minthk_analysis(formdiagram, envelope)

    elif objective == "MaximumThrust":
        analysis = Analysis.create_maxthrust_analysis(formdiagram, envelope)

    elif objective == "MaximumLoad":
        n = formobject.diagram.number_of_vertices()
        load_direction = zeros((n, 1))
        index_vertex = formobject.diagram.index_vertex()

        while True:
            formobject.show_vertices = list(formobject.diagram.vertices())
            vertices = formobject.select_vertices()
            formobject.redraw()

            if not vertices:
                break

            force = rs.GetReal(message="Load to assign to selected vertices (negative downwards):", number=-10)
            if not force:
                break

            for vertex in vertices:
                load_direction[index_vertex[vertex]] = force
            # Here we should add a vector to the Scene showing the load case that we are maximizing.

            add_loads = rs.GetString(message="Apply Loads on additional vertices?", strings=["Yes", "No"])
            rs.UnselectAllObjects()

            if add_loads == "Yes":
                pass
            else:
                break

        analysis = Analysis.create_max_load_analysis(formdiagram, envelope, load_direction=load_direction, solver="SLSQP", max_lambd=9999)

    elif objective == "SupportDisplacement":
        supports = list(formobject.diagram.supports())
        nb = len(supports)
        displacement_array = zeros((nb, 3))

        while True:
            formobject.show_vertices = supports
            vertices = formobject.select_vertices()
            formobject.redraw()

            if not vertices:
                break

            displ = rs.GetString(message="Vector to displace selected supports", defaultString="[-1, -1, 0]")

            if not displ:
                break

            displ_list = ast.literal_eval(displ)

            if len(displ_list) != 3:
                print("provide a 3x1 vector as shown as the example")
                break

            for vertex in vertices:
                displacement_array[supports.index(vertex)] = array(displ_list)
            # Here we should add a vector to the Scene showing the displacement that we are maximizing.

            add_vector = rs.GetString(message="Define additional displacement vectors?", strings=["Yes", "No"])
            rs.UnselectAllObjects()

            if add_vector == "Yes":
                pass
            else:
                break

        analysis = Analysis.create_compl_energy_analysis(formdiagram, envelope, solver="SLSQP", support_displacement=displacement_array)

    elif objective == "Bestfit":
        analysis = Analysis.create_bestfit_analysis(formdiagram, envelope)

    else:
        raise NotImplementedError

    analysis.optimiser.settings["printout"] = True  # need to be true so people see the fopt.
    analysis.apply_selfweight()
    analysis.apply_envelope()
    analysis.set_up_optimiser()
    analysis.run()

    # =============================================================================
    # Update scene
    # =============================================================================

    rs.UnselectAllObjects()

    formobject: RhinoFormDiagramObject = session.scene.find_by_itemtype(FormDiagram)  # type: ignore
    if not formobject:
        session.scene.add(formdiagram, name="FormDiagram", layer="Masonry::TNA::FormDiagram")  # type: ignore

    formobject.redraw()

    rs.Redraw()

    # =============================================================================
    # Save
    # =============================================================================

    # if session.settings.autosave:
    #     session.record(name="Analysis")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
