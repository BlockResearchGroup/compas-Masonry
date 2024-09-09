#! python3

import compas_masonry
from compas_rui.forms import AboutForm


def RunCommand(is_interactive):

    form = AboutForm(
        title=compas_masonry.title,
        description=compas_masonry.description,
        version=compas_masonry.__version__,
        website=compas_masonry.website,
        copyright=compas_masonry.__copyright__,
        license=compas_masonry.__license__,
    )

    form.show()


# =============================================================================
# Run as main
# =============================================================================

if __name__ == "__main__":
    RunCommand(True)
