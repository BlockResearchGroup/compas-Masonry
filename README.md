# COMPAS Masonry

> [!WARNING]
> This plugin is under active development,
> and its functionality will frequently change.

![COMPAS Masonry](compas-Masonry.png)

COMPAS Masonry is a plugin for Rhino for the assessment of masonry structures,
and for the stability analsis of Discrete Element Models in general.

The current version of this plugin is based on COMPAS 2 and is available for Rhino 8.

## Installation

To install COMPAS-Masonry, use Rhino's package manager Yak.
To open Yak, type `PackageManager` on the Rhino command line.

![COMPAS-Masonry installation with Yak](/gitbook/.gitbook/assets/COMPAS-Masonry_yak.png)

## COMPAS Packages

COMPAS-Masonry uses the following COMPAS packages:

* [compas](https://github.com/compas-dev/compas)
* [compas_assembly](https://github.com/blockresearchgroup/compas_assembly)
* [compas_model](https://github.com/blockresearchgroup/compas_model)
* [compas_rui](https://github.com/blockresearchgroup/compas_rui)
* [compas_session](https://github.com/blockresearchgroup/compas_session)

After installing RhinoVAULT with Yak, these requirements will be installed automatically if necessary.
The tool might be unresponsive during this process, which might take up to 1 or 2 mins.
The packages are installed in a separate virtual environment named `COMPAS-Masonry`.

> [!NOTE]
> Note that COMPAS-Masonry currently doesn't include any solvers
> (such as [compas_cra](https://github.com/blockresearchgroup/compas_cra)) yet.
> This is because they have dependencies that are still difficult to install in Rhino.

## User Interface

COMPAS-Masonry defines the following Rhino commands:

* `Masonry`
* `Masonry_session_undo`
* `Masonry_session_redo`
* `Masonry_session_open`
* `Masonry_session_save`
* `Masonry_scene_clear`
* `Masonry_scene_redraw`
* `Masonry_settings`

These commands can be executed using the Rhino command line (simply start typing the command name),
or with the corresponding buttons of the COMPAS-Masonry toolbar.

![COMPAS-Masonry toolbar](/gitbook/.gitbook/assets/COMPAS-Masonry_toolbar.png)

If the toolbar is not visible after installing COMPAS-Masonry,
you can load it from the "Toolbars" page.
To open the "Toolbars" page, type `Toolbar` on the Rhino command line...

![Rhino Toolbars](/gitbook/.gitbook/assets/Rhino_toolbars.png)

## Documentation

For further "getting started" instructions, a tutorial, examples, and an detailed description of the individual commands and the user interface, please check out the online documentation here: [COMPAS-Masonry Gitbook](https://blockresearchgroup.gitbook.io/COMPAS-Masonry)

## Issues

Please report problems using the issue tracker of the github repo: <https://github.com/blockresearchgroup/compas-Masonry/issues>
