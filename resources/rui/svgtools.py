"""Shared SVG handling for the icon pipeline.

Three jobs, all of them things Rhino's icon format needs and a design tool does
not produce:

1. **Flatten `<style>` CSS into inline presentation attributes.** Illustrator
   exports `class="cls-1"` plus a `<style>` block. The icons that already work in
   this plugin carry inline attributes and no CSS at all, so relying on Rhino's
   SVG renderer supporting embedded stylesheets is a bet with no upside — flatten
   instead and the question disappears.

2. **Wrap in Rhino's outer SVG.** Rhino stores a 48pt outer `<svg>` carrying
   `fill-dark` / `stroke-dark`, with the real icon nested inside. Those two
   attributes are how ONE piece of artwork serves both the light and dark themes.

3. **Rasterize** to PNG, for the rhproj's rendered cache and the toolbar sprite
   sheet. Uses `rsvg-convert` (librsvg), which honours CSS and gradients.
"""

import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

# Declarations worth promoting to attributes. Anything else in the CSS is left
# alone rather than guessed at.
PAINT_PROPS = {
    "fill",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "stroke-dasharray",
    "opacity",
    "fill-opacity",
    "stroke-opacity",
    "fill-rule",
}

RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)


def parse_css(text):
    """{class name: {property: value}} from a simple `<style>` block.

    Handles the shape Illustrator emits — `.cls-1, .cls-2 { fill: none; }` — and
    ignores anything that is not a plain class selector.
    """
    out = {}
    for selectors, body in RULE_RE.findall(text):
        decls = {}
        for decl in body.split(";"):
            if ":" not in decl:
                continue
            prop, _, value = decl.partition(":")
            prop, value = prop.strip(), value.strip()
            if prop in PAINT_PROPS:
                # "0.25px" is not valid as an SVG attribute value
                decls[prop] = value[:-2].strip() if value.endswith("px") else value
        if not decls:
            continue
        for selector in selectors.split(","):
            selector = selector.strip()
            if selector.startswith(".") and " " not in selector:
                out.setdefault(selector[1:], {}).update(decls)
    return out


def flatten_css(svg_text):
    """Inline every `<style>` class as presentation attributes; drop the style block.

    An attribute already present on the element wins, matching CSS specificity
    closely enough for artwork of this shape.

    UNUSED, and kept only so the reasoning survives with it. Both icon pipelines
    stopped calling this — make_icons.py on 2026-08-28, set_rhproj_icons.py after
    it shipped a broken 0.5.2 toolbar. Flattening CANNOT preserve
    `mix-blend-mode`, `isolation` or `clip-path`, which have no presentation-
    attribute form, and promoting them into PAINT_PROPS does not bring them back.
    The damage looks like wrong z-order: an element that is invisible by design
    under a blend mode becomes an opaque block without it.

    Do not reintroduce this without a rendered before/after comparison. Every
    consumer here honours a <style> block already.
    """
    root = ET.fromstring(svg_text)

    classes = {}
    for parent in root.iter():
        for style in list(parent):
            if style.tag == f"{{{SVG_NS}}}style":
                classes.update(parse_css("".join(style.itertext())))
                parent.remove(style)

    if classes:
        for element in root.iter():
            names = element.get("class")
            if not names:
                continue
            for name in names.split():
                for prop, value in classes.get(name, {}).items():
                    if prop not in element.attrib:
                        element.set(prop, value)
            del element.attrib["class"]

    return ET.tostring(root, encoding="unicode")


def wrap_for_rhino(svg_text, fill_dark="#FFF", stroke_dark="#FFF", size=48):
    """Nest an icon inside Rhino's outer SVG, the format the rhproj stores.

    `fill_dark` / `stroke_dark` recolour the artwork for the dark theme. The
    icons this plugin shipped with were filled Font Awesome glyphs and used
    `stroke-dark="none"`; artwork that is drawn with STROKES needs a real colour
    there or it disappears against a dark background.
    """
    inner = svg_text.strip()
    inner = re.sub(r"^<\?xml[^>]*\?>\s*", "", inner)  # a nested doc takes no declaration
    return (
        f'<svg width="{size}" height="{size}" version="1.1" '
        f'xmlns="{SVG_NS}" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0pt 0pt {size}pt {size}pt" '
        f'fill-dark="{fill_dark}" stroke-dark="{stroke_dark}">\n'
        f"  {inner}\n"
        f"</svg>"
    )


BLACKS = {"#000", "#000000", "black", "rgb(0,0,0)"}

# A "rich black" like #231f20 is not in BLACKS but is just as invisible on a dark
# toolbar. Treat a colour as black when it is BOTH dark and unsaturated: that
# catches greys and off-blacks while leaving a deliberate hue alone, however dark
# it happens to be. Changing someone's accent colour is a design decision, not a
# legibility fix.
NEAR_BLACK_LUMINANCE = 60
NEAR_BLACK_CHROMA = 30


def _is_near_black(value):
    value = value.strip().lower()
    if value in BLACKS:
        return True
    if not value.startswith("#"):
        return False
    h = value[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return False
    try:
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return False
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    chroma = max(r, g, b) - min(r, g, b)
    return luminance < NEAR_BLACK_LUMINANCE and chroma < NEAR_BLACK_CHROMA


def recolor_black(svg_text, target):
    """Repaint black artwork as `target`, leaving deliberate accent colours alone.

    **The toolbar sprite sheet gets no dark-mode help from Rhino.** `fill-dark` /
    `stroke-dark` are Rhino attributes read from the rhproj SVG (System A); the
    RUI sheet is a rasterized PNG and Rhino cannot recolour a bitmap. So artwork
    drawn in black — which is correct for a light UI — is close to invisible on a
    dark toolbar, and the fix has to happen before rasterization.

    Only near-black is touched, so a red or purple accent survives.
    """
    if not target:
        return svg_text

    def repaint(match):
        attr, quote, value = match.group(1), match.group(2), match.group(3)
        return f"{attr}={quote}{target if _is_near_black(value) else value}{quote}"

    # presentation attributes (flatten_css has already inlined the CSS)
    svg_text = re.sub(r'\b(fill|stroke|stop-color)=(["\'])(.*?)\2', repaint, svg_text)
    # any leftover inline style declarations
    for prop in ("fill", "stroke", "stop-color"):
        svg_text = re.sub(
            rf"\b{prop}:\s*(#000000|#000|black)\b",
            f"{prop}:{target}",
            svg_text,
            flags=re.I,
        )

    # IMPLICIT black. An element with no `fill` at all paints black by default, so
    # rewriting explicit values misses it entirely — which is how half the shapes
    # in an icon stayed dark while the recolour reported success. A fill on the
    # ROOT is inherited by exactly those elements, and loses to any child that
    # states its own (including `none` and `url(#gradient)`).
    def add_root_fill(match):
        tag = match.group(0)
        return tag if re.search(r'\bfill=', tag) else f"{tag[:-1]} fill=\"{target}\">"

    return re.sub(r"<svg\b[^>]*>", add_root_fill, svg_text, count=1)


def enforce_min_stroke(svg_text, minimum):
    """Raise hairline strokes to `minimum`, in user units of the icon's viewBox.

    A `stroke-width` of 0.25 in a 32-unit viewBox is a quarter of a pixel at a
    32px tile: antialiasing turns it into a faint grey smear rather than a line.
    Widths already above the floor are left exactly as drawn.
    """
    if not minimum:
        return svg_text

    def raise_width(match):
        attr, quote, value = match.group(1), match.group(2), match.group(3)
        try:
            width = float(value.replace("px", "").strip())
        except ValueError:
            return match.group(0)
        return f"{attr}={quote}{max(width, minimum):g}{quote}"

    svg_text = re.sub(r'\b(stroke-width)=(["\'])(.*?)\2', raise_width, svg_text)

    def raise_decl(match):
        try:
            width = float(match.group(1).replace("px", "").strip())
        except ValueError:
            return match.group(0)
        return f"stroke-width:{max(width, minimum):g}"

    return re.sub(r"\bstroke-width:\s*([0-9.]+)(?:px)?", raise_decl, svg_text)


def have_rasterizer():
    return shutil.which("rsvg-convert") is not None


def rasterize(svg_text, size):
    """Render SVG text to PNG bytes at size x size. Requires `rsvg-convert`."""
    if not have_rasterizer():
        raise RuntimeError("rsvg-convert not found. Install it with:  brew install librsvg")
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg_text)
        path = f.name
    try:
        return subprocess.run(
            ["rsvg-convert", "-w", str(size), "-h", str(size), "-f", "png", path],
            check=True,
            capture_output=True,
        ).stdout
    finally:
        Path(path).unlink(missing_ok=True)


def icon_paths(icondir, commands):
    """{command: Path} for icons named exactly after their command."""
    icondir = Path(icondir)
    return {name: icondir / f"{name}.svg" for name in commands}
