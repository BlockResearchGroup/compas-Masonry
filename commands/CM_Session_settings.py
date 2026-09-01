#! python3
# venv: brg-csd
# r: compas_masonry>=0.4.1

"""Session_settings_WIP_options — RhinoCommon variant of Session_settings_WIP.

Demonstrates the point of compas_masonry.inputs: one pydantic settings model,
two renderers.

- Dialog      : compas_masonry.forms.settings.SettingsForm (Eto), all field
                types including colors.
- CommandLine : Options.from_model(...), same fields on the command line, using
                the same title / default / ge / le metadata. Types without a
                command line widget (colors, tuples, lists) are skipped, so the
                dialog stays the complete editor.

The "Input" section holds `dialog_input`, which decides how *every other*
command asks for its parameters: command line options, or the Eto renderer in
compas_masonry.forms.options.
"""

import pathlib

from compas_masonry.forms.settings import SettingsForm
from compas_masonry.inputs import Options
from compas_masonry.inputs import choose
from compas_masonry.session import MasonrySession as Session
from compas_rui.feedback import warn

# =============================================================================
# Command
# =============================================================================


def edit_on_commandline(settings, title):
    """Render a pydantic settings model as command line options."""
    options = Options.from_model(settings, prompt=title)
    if not options.fields:
        return warn(f"No {title} settings can be edited on the command line. Use the dialog.")

    skipped = len(type(settings).model_fields) - len(options.fields)
    if skipped:
        print(f"{skipped} {title} setting(s) have no command line widget (colors, tuples, ...). Use the dialog for those.")

    # explicit: the user just picked "CommandLine", so ignore settings.dialog_input
    values = options.get(dialog=False)
    if values is None:
        return

    try:
        options.apply(settings, values)
    except Exception as e:  # pydantic validation happens on assignment
        return warn(f"Invalid {title} settings: {e}")


def RunCommand():
    session = Session(basedir=pathlib.Path().home() / ".compas_session", name="COMPAS-Masonry")

    sections = {
        # the top-level settings (autoupdate, autosave, dialog_input); the
        # nested sections below are skipped by both renderers
        "Input": session.settings,
        "FormDiagram": session.settings.formdiagram,
        "Envelope": session.settings.envelope,
        "BlockModel": session.settings.blockmodel,
    }

    option = choose("Settings section (escape to exit)", list(sections.keys()))
    if option is None:
        return

    settings = sections[option]

    renderer = choose("Edit in", ["Dialog", "CommandLine"], default="Dialog")
    if renderer is None:
        return

    if renderer == "Dialog":
        form = SettingsForm(settings, title=option)
        form.show()
    else:
        edit_on_commandline(settings, option)

    show_intrados = session.settings.envelope.show_intrados
    show_middle = session.settings.envelope.show_middle
    show_extrados = session.settings.envelope.show_extrados
    show_fill = session.settings.envelope.show_fill

    intradosobj = session.scene.find_by_name("Intrados")
    if intradosobj:
        intradosobj.show = show_intrados

    middleobj = session.scene.find_by_name("Middle")
    if middleobj:
        middleobj.show = show_middle

    extradosobj = session.scene.find_by_name("Extrados")
    if extradosobj:
        extradosobj.show = show_extrados

    fillobj = session.scene.find_by_name("Fill")
    if fillobj:
        fillobj.show = show_fill

    session.redraw()

    # Editing `session.settings` mutates an in-memory pydantic model and writes
    # NOTHING: the settings file is only produced by `dump()`, which `record()`
    # calls. Without this the whole command was a no-op across a Rhino restart —
    # every other command that changes session state records, and this one did
    # not. Recording also puts settings under undo/redo, which is consistent
    # with how the rest of the session behaves.
    session.record("Session settings")


# TO_DO: visualize the BlockModel settings


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand()
