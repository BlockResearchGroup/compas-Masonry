# COMPAS Masonry

![COMPAS Masonry](compas-Masonry.png)

COMPAS Masonry is a plugin for Rhino for the assessment of masonry structures. The current version of this plugin is based on COMPAS 2 and is available for Rhino 8.

> [!WARNING]
> This plugin is under active development,
> and uses the still somewhat unstable CPython infrastructure
> of Rhino 8 through the new ScriptEditor.
> Therefore, unexpected errors may occur.

## Installation

To install COMPAS Masonry, use Rhino's package manager Yak.

![COMPAS Masonry installation with Yak](resources/images/COMPAS-Masonry_yak.png)

## COMPAS Packages

Masonry uses the following COMPAS packages:

* [compas](https://github.com/compas-dev/compas)
* [compas_assembly](https://github.com/blockresearchgroup/compas_assembly)
* [compas_cra](https://github.com/blockresearchgroup/compas_cra)
* [compas_model](https://github.com/blockresearchgroup/compas_model)
* [compas_rui](https://github.com/blockresearchgroup/compas_rui)
* [compas_session](https://github.com/blockresearchgroup/compas_session)

After installing COMPAS Masonry with Yak, you can check if all requirements are installed using the command `Masonry_reqs_check`.

### Basic Users

Missing requirements can be installed automatically using the command `Masonry_reqs_install`.
This command uses Rhino's built in installation mechanism for Python packages (`# r: ...`).

### Advanced Users

If you use Rhino for scripting, and if you have other COMPAS packages installed, or plan to install them in the future, we recommend to install Masonry's requirements manually using `pip`.

> [!WARNING]
> `pip` based installations and `# r: ...` based installations should not be mixed,
> since this will create conflicts between packages and package versions.

## User Interface

Masonry defines the following commands:

* `Masonry`
* `Masonry_pattern`
* `Masonry_pattern_modify`
* `Masonry_pattern_relax`
* `Masonry_pattern_supports`
* `Masonry_pattern_boundaries`
* `Masonry_form`
* `Masonry_force`
* `Masonry_tna_horizontal`
* `Masonry_tna_vertical`
* `Masonry_form_modify`
* `Masonry_force_modify`
* `Masonry_thrust_modify`
* `Masonry_scene_clear`
* `Masonry_scene_redraw`
* `Masonry_session_undo`
* `Masonry_session_redo`
* `Masonry_session_open`
* `Masonry_session_save`
* `Masonry_settings`
* `Masonry_reqs_check`
* `Masonry_reqs_install`

These commands can be executed at the Rhino Command Prompt (simply start typing the command name),
or using the COMPAS Masonry toolbar.

![COMPAS Masonry toolbar](resources/images/COMPAS-Masonry_toolbar.png)

## Documentation

For further "getting started" instructions, a tutorial, examples, and an detailed description of the individual commands and the user interface, please check out the online documentation here: [COMPAS Masonry Gitbook](https://blockresearchgroup.gitbook.io/compas-Masonry)

## Issue Tracker

If you find a bug or if you have a problem with running the code, please file an issue on the [Issue Tracker](https://github.com/blockresearchgroup/compas-Masonry/issues).
