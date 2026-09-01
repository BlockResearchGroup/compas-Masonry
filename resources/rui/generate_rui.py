"""Generate resources/COMPAS-Masonry.rui from resources/rui/ui.json.

Uses compas_rui's own RUI compiler (compas_rui.rui.Rui) — the same mechanism
BRG uses for their plugin toolbars, and compas_rui is already a plugin
dependency. Run from the repo root:

    python resources/rui/generate_rui.py

To change the layout, edit ui.json (commands / toolbars with
{"type": "separator"} items / toolbargroups) and re-run.

## Icons

A RUI carries ONE sprite sheet per button size, and each command references a
tile by index. In ui.json:

    "icons": {"bitmap": "icons.png", "images": ["CM_Model_blocks", ...]}
    ...
    {"name": "CM_Model_blocks", "script": "...", "icon": 0}

`icons.images` is an ordered list of names — its *position* is what `"icon"`
refers to; the names are documentation. `make_icons.py` builds `icons.png` from
the SVGs in `resources/icons/` and writes both the sheet and these ui.json fields.

**Run this script AFTER make_icons.py, every time.** Rhino reads the compiled
.rui and nothing else, so a rebuilt sheet that was never compiled in leaves the
toolbars showing the previous artwork.

**A RUI holds three sheets — 16px, 24px and 32px tiles — and Rhino picks one
according to the toolbar's button size.** `compas_rui.rui.Rui.add_bitmap` fills
only `large_bitmap` (32px) and leaves the other two as an empty placeholder, so
icons appear only when buttons are set to large, and silently vanish at the other
two sizes. `_fill_all_bitmap_sizes` below downsamples the 32px sheet into the
16px and 24px slots after compas_rui has run. Remove it if that is ever fixed
upstream.

Equivalent CLI (large size only, for the reason above):

    python -m compas_rui.rui resources/rui/ui.json resources/COMPAS-Masonry.rui
"""

import base64
import io
import json
import pathlib
import re
import uuid
import xml.etree.ElementTree as ET

from compas_rui.rui import Rui

HERE = pathlib.Path(__file__).parent
UI = HERE / "ui.json"
OUT = HERE.parent / "COMPAS-Masonry.rui"

# STABLE collection guid — do not change it.
#
# `Rui.__init__` does `self.guid = guid or uuid.uuid4()`, so left to itself every
# regeneration produces a NEW guid, and Rhino identifies a toolbar collection by
# exactly that. The consequence is nasty and quiet: Rhino keeps the previously
# loaded collection registered and showing the OLD artwork, while the rebuilt file
# registers as an unrelated one. It looks like "my icons did not update".
#
# Pinning it means a rebuild REPLACES the collection Rhino already knows.
COLLECTION_GUID = "35a29155-639d-45c1-bf37-6341627df120"

# tile size of each sheet, matching compas_rui's item_width/item_height
SIZES = {"small_bitmap": 16, "normal_bitmap": 24, "large_bitmap": 32}

GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b")


def _pin_inner_guids(ruipath) -> int:
    """Rewrite every guid below the collection as a deterministic uuid5.

    COLLECTION_GUID above pins only the collection itself. Everything inside it
    — toolbar groups, toolbars, buttons, macros — is a fresh `uuid.uuid4()` from
    compas_rui on every run, so two builds from identical inputs never produce
    the same bytes. Measured 2026-09-01: 142 lines of pure guid churn between
    consecutive runs with no input change.

    That costs three things. The `.rui` is a tracked artifact, so every build
    dirties it with a diff nobody wrote. `git diff` can no longer answer whether
    a rebuild changed anything real. And Rhino identifies buttons by guid, so a
    rebuild discards any toolbar customisation a user has made.

    uuid5 is a hash, not a random draw: the same inputs give the same guids, on
    any machine. Keying on order of first appearance is enough because that order
    is driven by ui.json, and remapping consistently keeps every internal
    reference intact — a `<left_macro_id>` still points at its macro.

    The base64 sprite sheets cannot collide with the pattern: standard base64 has
    no `-`.
    """
    path = pathlib.Path(ruipath)
    mapping = {}

    def pin(match):
        old = match.group(0)
        if old.lower() == COLLECTION_GUID:
            return old
        if old not in mapping:
            mapping[old] = str(uuid.uuid5(uuid.UUID(COLLECTION_GUID), str(len(mapping))))
        return mapping[old]

    path.write_text(GUID_RE.sub(pin, path.read_text()))
    return len(mapping)


def _fill_all_bitmap_sizes(ruipath, uipath) -> bool:
    """Write the 16px and 24px sheets that compas_rui leaves empty.

    Returns True if sheets were written, False if there is no icon sheet to
    resize (no icons configured, or Pillow missing).
    """
    ui = json.loads(pathlib.Path(uipath).read_text())
    sheet = (ui.get("icons") or {}).get("bitmap")
    if not sheet:
        return False

    sheetpath = pathlib.Path(uipath).parent / sheet
    if not sheetpath.exists():
        print(f"  icons.bitmap points at {sheetpath}, which does not exist")
        return False

    try:
        from PIL import Image
    except ImportError:
        print("  Pillow not installed: only the 32px sheet is filled, so icons")
        print("  will show only when the toolbar uses large buttons.")
        return False

    source = Image.open(sheetpath).convert("RGBA")
    ntiles = source.width // SIZES["large_bitmap"]

    tree = ET.parse(ruipath)
    root = tree.getroot()
    bitmaps = root.find("bitmaps")

    for name, size in SIZES.items():
        if size == SIZES["large_bitmap"]:
            continue  # compas_rui already wrote this one
        resized = source.resize((size * ntiles, size), Image.LANCZOS)
        buffer = io.BytesIO()
        resized.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        bitmaps.find(name).find("bitmap").text = encoded

    tree.write(ruipath, encoding="utf-8", xml_declaration=True)
    print(f"  filled the 16px and 24px sheets ({ntiles} tiles each)")
    return True


if __name__ == "__main__":
    rui = Rui.from_json(str(UI), str(OUT), guid=COLLECTION_GUID)
    rui.write()
    print(f"wrote {OUT}")
    print(f"  collection guid {COLLECTION_GUID} (stable, so a rebuild replaces rather than adds)")
    # Before the sheets go in, so the regex walks a small file rather than 20k
    # of base64 that cannot match it anyway.
    print(f"  pinned {_pin_inner_guids(str(OUT))} inner guids (deterministic, so a rebuild is byte-identical)")
    _fill_all_bitmap_sizes(str(OUT), str(UI))
