#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Model_material_options — RhinoCommon variant of Model_material.

Differences with Model_material:
- Create asks for material type and source in one prompt (two options side by
  side) instead of two sequential questions.
- Predefined materials are printed as a table with all their values *before*
  the pick, so the choice is informed, and the pick list carries a "Custom"
  entry that leads into the custom generation.
- The custom properties (name, fck, ft, Ecm, density, poisson) are a single
  prompt with six options, seeded with the current values when modifying, and
  offer "Back" to step to the previous window instead of cancelling.
- Material selection uses Rhino's list dialog (unbounded number of materials,
  labels with spaces/parentheses).

Semantics are unchanged: see Model_material.
"""

import pathlib

import rhinoscriptsyntax as rs  # type: ignore

from compas_dem.material import GenericMaterial
from compas_dem.material import Stone
from compas_dem.models import BlockModel
from compas_masonry.inputs import BACK
from compas_masonry.inputs import Options
from compas_masonry.inputs import choose
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import confirm
from compas_rui.feedback import warn

MATERIAL_TYPES = {"Stone": Stone, "Generic": GenericMaterial}


def material_label(material) -> str:
    return f"{material.name} ({material.__class__.__name__})"


def pick_material(materials, message="Select a material"):
    """Pick a material from a list dialog.

    Labels are index-prefixed so that identically named materials stay
    distinguishable, and the index is used to resolve the selection.
    """
    labels = [f"{i}: {material_label(m)}" for i, m in enumerate(materials)]
    label = rs.ListBox(labels, message=message, title="Materials")
    if not label:
        return None
    return materials[int(label.split(":")[0])]


def print_predefined(cls) -> list:
    """Print every predefined material of `cls` with its values, in a table.

    Dev notes: the values have to be visible in the command window *before*
    picking, so the choice is informed.

    Returns the material keys, in the printed order.
    """
    # keys of cls.predefined_material — "fck" since the compas_dem rename, so a
    # stale "fc" here would print "-" for every material instead of its strength
    props = ["fck", "ft", "Ecm", "density", "poisson"]
    keys = sorted(cls.predefined_material)

    rows = [[key] + [cell(cls.predefined_material[key].get(p)) for p in props] for key in keys]
    print_table(["material"] + props, rows)

    return keys


def cell(value) -> str:
    """One table cell: a compact number, or "-" for a missing value.

    `str(value)` on a float can run to 18 characters (0.19999999999999998), which
    is wider than any fixed column and pushed every cell after it out of line.
    A float is only ever read here, never parsed back, so 4 significant digits
    is enough and always fits.
    """
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def print_table(headers, rows) -> None:
    """Print a table whose columns are sized to their contents.

    Widths are measured rather than assumed: a hardcoded width silently breaks
    the row whenever one value is wider than it, and every column after that one
    shifts.
    """
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) if rows else len(str(h)) for i, h in enumerate(headers)]

    def line(cells):
        # first column left-aligned (names), the numbers right-aligned
        out = [str(cells[0]).ljust(widths[0])]
        out += [str(c).rjust(w) for c, w in zip(cells[1:], widths[1:])]
        return "  ".join(out)

    header = line(headers)
    print(header)
    print("-" * len(header))
    for row in rows:
        print(line(row))


def prompt_properties(defaults, title="Material properties", back=False):
    """Ask for all custom material properties at once, seeded with `defaults`.

    Returns a dict of {name, fck, ft, Ecm, density, poisson}, BACK, or None if
    cancelled. fck/ft/Ecm accept 0 to mean "unset" (None), as in Model_material.
    """
    options = Options(title, back=back)
    options.add_text("name", defaults.get("name") or "Material", keyword="Name")
    options.add_number("fck", defaults.get("fck") or 0.0, minimum=0.0, keyword="Fck", units="MPa", prompt="Characteristic compressive strength fck (0 = unset)")
    options.add_number("ft", defaults.get("ft") or 0.0, minimum=0.0, keyword="Ft", units="MPa", prompt="Tensile strength ft (0 = derive from fck)")
    # MPa, not GPa: the predefined values are 20000 / 30000
    options.add_number("Ecm", defaults.get("Ecm") or 0.0, minimum=0.0, keyword="Ecm", units="MPa", prompt="Modulus of elasticity Ecm (0 = unset)")
    options.add_number("density", defaults.get("density") or 2400.0, minimum=0.0, keyword="Density", units="kg/m3", prompt="Density")
    options.add_number("poisson", defaults.get("poisson") or 0.2, minimum=0.0, keyword="Poisson", prompt="Poisson's ratio")

    values = options.get()
    if values is None or values is BACK:
        return values

    return {
        "name": values["name"],
        "fck": values["fck"] or None,
        "ft": values["ft"] or None,
        "Ecm": values["Ecm"] or None,
        "density": values["density"],
        "poisson": values["poisson"],
    }


def material_properties(material) -> dict:
    """Extract the editable properties of an existing material as a dict."""
    return {
        "name": material.name,
        "fck": material.fck,
        "ft": material.ft,
        "Ecm": material.Ecm,
        "density": material.density,
        "poisson": material.poisson,
    }


CUSTOM = "Custom (enter the values)"


def create_material(model):
    """Create a material: type + source in one window, then predefined or custom.

    The prompts are a loop so that "Back" steps to the previous window instead
    of cancelling the whole command.
    """
    while True:
        options = Options("New material")
        options.add_list("kind", list(MATERIAL_TYPES.keys()), keyword="Type")
        options.add_toggle("source", False, off="Predefined", on="Custom", text=True, keyword="Source")

        values = options.get()
        if values is None:
            return

        kind = values["kind"]
        cls = MATERIAL_TYPES[kind]
        custom = values["source"] == "Custom"

        if not custom:
            # print the whole table first, so the values are visible before picking
            keys = print_predefined(cls)
            choice = rs.ListBox(keys + [CUSTOM], message=f"Predefined {kind} material", title=kind)
            if not choice:
                return
            if choice == CUSTOM:
                custom = True  # the list keeps a way into the custom generation
            else:
                material = cls.from_predefined_material(choice)
                model.add_material(material)
                print(f"Added material: {material_label(material)}")
                return

        props = prompt_properties({}, title=f"New {kind} material", back=True)
        if props is BACK:
            continue
        if props is None:
            return

        material = cls(**props)
        model.add_material(material)
        print(f"Added material: {material_label(material)}")
        return


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    model: BlockModel = session.model
    if model is None:
        return warn("No existing BlockModel in session. Please create one first.")

    option = choose("Model_material", ["Create", "Modify", "Remove", "Clear", "Duplicate"])
    if option is None:
        return

    # Each branch below has its own bail-outs, so this can fire for a command the
    # user then cancels. That costs at most ONE extra snapshot in the whole
    # session — `ensure_baseline` is a no-op once history exists — and the state
    # it captures is a legitimate one to return to.
    session.ensure_baseline()

    # =============================================================================
    # Create
    # =============================================================================

    if option == "Create":
        create_material(model)

    # =============================================================================
    # Modify (mutates in place, so existing block assignments stay valid)
    # =============================================================================

    elif option == "Modify":
        materials = list(model.materials())
        if not materials:
            return warn("No materials in the model yet. Run Model_material > Create first.")

        material = pick_material(materials, message="Material to modify")
        if material is None:
            return

        props = prompt_properties(material_properties(material), title=f"Modify {material.name}")
        if props is None:
            return

        material.name = props["name"]
        material.fck = props["fck"]
        material.ft = props["ft"]
        material.Ecm = props["Ecm"]
        material.density = props["density"]
        material.poisson = props["poisson"]
        print(f"Modified material: {material_label(material)}")

    # =============================================================================
    # Remove (drop from model, unassign from any blocks that referenced it)
    # =============================================================================

    elif option == "Remove":
        materials = list(model.materials())
        if not materials:
            return warn("No materials in the model to remove.")

        material = pick_material(materials, message="Material to remove")
        if material is None:
            return

        guid = str(material.guid)
        for element in model.elements():
            if element._material == guid:
                element._material = None
        model._materials.pop(guid, None)
        print(f"Removed material: {material_label(material)}")
        session.redraw()

    # =============================================================================
    # Clear (remove every material and unassign all blocks)
    # =============================================================================

    elif option == "Clear":
        if not list(model.materials()):
            return warn("No materials in the model to clear.")

        if not confirm("Clear ALL materials?"):
            return

        for element in model.elements():
            element._material = None
        model._materials.clear()
        print("Cleared all materials.")
        session.redraw()

    # =============================================================================
    # Duplicate (same type, copied properties, ' copy' suffix)
    # =============================================================================

    elif option == "Duplicate":
        materials = list(model.materials())
        if not materials:
            return warn("No materials in the model to duplicate.")

        material = pick_material(materials, message="Material to duplicate")
        if material is None:
            return

        props = material_properties(material)
        props["name"] = f"{props['name']} copy"
        duplicate = type(material)(**props)
        model.add_material(duplicate)
        print(f"Duplicated material: {material_label(duplicate)}")

    # Persist the mutated model so the change survives to the next command.
    session.save_model()
    session.record(f"Material: {option}")


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
