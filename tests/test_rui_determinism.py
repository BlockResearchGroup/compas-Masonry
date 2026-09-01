"""Regenerating the toolbar must produce the same bytes every time.

`compas_rui` draws a fresh `uuid.uuid4()` for every toolbar, group, button and
macro, so before 2026-09-01 two builds from identical inputs differed by 142
lines of pure guid churn. That is worse than noise: the `.rui` is a tracked
artifact, so `git diff` could no longer answer whether a rebuild changed
anything real, and Rhino identifies buttons by guid, so every rebuild threw away
whatever toolbar customisation a user had made.

`generate_rui.py:_pin_inner_guids` replaces them with `uuid5` hashes keyed on the
collection guid and order of first appearance. These tests read the tracked file
only — no `compas_rui`, no Pillow, no Rhino — so they fail if someone regenerates
with the pinning removed, hand-edits a guid, or upgrades `compas_rui` into
emitting a different number of elements.
"""

import collections
import pathlib
import re
import uuid
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUI = ROOT / "resources" / "COMPAS-Masonry.rui"
GENERATOR = ROOT / "resources" / "rui" / "generate_rui.py"

GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b")


@pytest.fixture(scope="module")
def collection_guid():
    """Read COLLECTION_GUID out of the generator, so the two cannot drift apart."""
    match = re.search(r'^COLLECTION_GUID = "([^"]+)"', GENERATOR.read_text(), re.M)
    assert match, "COLLECTION_GUID not found in generate_rui.py"
    return match.group(1)


@pytest.fixture(scope="module")
def root():
    return ET.parse(RUI).getroot()


def test_collection_guid_is_the_pinned_one(root, collection_guid):
    """Rhino keys the collection on this. A new one registers as an unrelated
    toolbar while the old one stays loaded, showing the previous artwork."""
    assert root.get("guid") == collection_guid


def test_every_inner_guid_is_deterministic(collection_guid):
    """The whole file must be reproducible from the collection guid alone.

    Rebuilds the expected mapping the same way the generator does — first
    appearance order, uuid5 under the collection namespace — and insists the
    tracked file already matches it. A uuid4 anywhere fails here.
    """
    namespace = uuid.UUID(collection_guid)
    seen = {}
    for found in GUID_RE.findall(RUI.read_text()):
        if found.lower() == collection_guid:
            continue
        if found not in seen:
            seen[found] = str(uuid.uuid5(namespace, str(len(seen))))
        assert found == seen[found], f"{found} is not the uuid5 the generator would produce -- was the .rui regenerated without _pin_inner_guids, or a guid edited by hand?"

    assert seen, "no inner guids found at all -- did the .rui format change?"


def test_no_reference_dangles(root):
    """A guid remap that collapsed two distinct guids, or missed a reference,
    leaves a button wired to nothing. The RUI still loads; the button just does
    nothing when pressed."""
    macros = {item.get("guid") for item in root.iter("macro_item")}
    bars = {bar.get("guid") for bar in root.iter("tool_bar")}

    refs = [element.text for tag in ("left_macro_id", "right_macro_id") for element in root.iter(tag) if element.text and element.text != "None"]
    assert [ref for ref in refs if ref not in macros] == []
    assert [ref for ref in root.iter("tool_bar_id") if ref.text not in bars] == []


def test_the_toolbar_shape_is_pinned(root):
    """`rhinocode project build` generates a toolbar with no ordering and no
    separators. If these numbers change, check the shipped `.rui` is still the
    designed one — see temp/ICON_BUILD_DIAGNOSIS.md."""
    styles = collections.Counter(item.get("button_style") for item in root.iter("tool_bar_item"))
    assert styles["normal"] == 22
    assert styles["spacer"] == 4
