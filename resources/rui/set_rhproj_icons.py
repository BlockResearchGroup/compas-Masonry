"""STEP 2 — bind resources/icons/<command>.svg into COMPAS-Masonry.rhproj.

This is icon System A: one SVG per command, stored inline, driving the Script
Editor and the command palette. See temp/wiki_icons.md §2.1.

For each codes[] entry it REPLACES image wholesale — wrapping the icon in Rhino's
dark-aware outer SVG and rendering the 24x24 light/dark PNG cache. Replacing
rather than merging is what removes any link to the old artwork.

The SVG is stored AS DRAWN. This script used to flatten the <style> block into
presentation attributes first, which silently destroyed `mix-blend-mode`,
`isolation` and `clip-path` — see the comment at the call site.

    python resources/rui/set_rhproj_icons.py --dry-run
    python resources/rui/set_rhproj_icons.py

The entry's `id` is never touched: it is the identity of the command as far as
Rhino is concerned, and a new one makes Rhino treat it as a different command.
"""

import argparse
import base64
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from svgtools import have_rasterizer  # noqa: E402
from svgtools import rasterize  # noqa: E402
from svgtools import wrap_for_rhino  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent.parent
RHPROJ = ROOT / "COMPAS-Masonry.rhproj"
ICONS = ROOT / "resources" / "icons"
RENDER = 24  # the size the rhproj caches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    ap.add_argument("--fill-dark", default="#FFF")
    ap.add_argument("--stroke-dark", default="#FFF", help='"none" for filled artwork')
    args = ap.parse_args()

    proj = json.loads(RHPROJ.read_text(), object_pairs_hook=collections.OrderedDict)

    if not have_rasterizer():
        print("rsvg-convert not found — install with:  brew install librsvg")
        return 1

    done, missing = 0, []
    for entry in proj["codes"]:
        name = entry["title"]
        source = ICONS / f"{name}.svg"
        if not source.exists():
            missing.append(name)
            continue

        # Deliberately NOT flatten_css — the same fix make_icons.py took on
        # 2026-08-28, applied here a release later.
        #
        # Flattening a <style> block into presentation attributes cannot preserve
        # `mix-blend-mode`, `isolation` or `clip-path`: those have no attribute
        # form, so promoting them into PAINT_PROPS does not help either. Dropping
        # them changes what the icon MEANS — `.k { fill: #fff }` under
        # `mix-blend-mode: multiply` is invisible by design, and without the blend
        # it paints an opaque white block over the artwork behind it. That is the
        # "colours mixed black and white, artifacts" seen in 0.5.2.
        #
        # Both consumers below cope with the <style> block: `rasterize` shells out
        # to rsvg-convert, which honours CSS (measured pixel-exact on the 22-tile
        # sheet), and `wrap_for_rhino` only nests the text inside Rhino's outer
        # <svg>. CM_Problem_displacements.svg is the only icon using all three
        # CSS-only properties at once, which is why it was the one that broke.
        wrapped = wrap_for_rhino(source.read_text(), args.fill_dark, args.stroke_dark)
        png = base64.b64encode(rasterize(wrapped, RENDER)).decode()

        entry["image"] = collections.OrderedDict(
            [
                ("light", collections.OrderedDict([("type", "svg"), ("data", base64.b64encode(wrapped.encode()).decode())])),
                (
                    "rendered",
                    collections.OrderedDict(
                        [
                            ("light", collections.OrderedDict([("bytes", png), ("width", RENDER), ("height", RENDER)])),
                            ("dark", collections.OrderedDict([("bytes", png), ("width", RENDER), ("height", RENDER)])),
                        ]
                    ),
                ),
            ]
        )
        done += 1

    if missing:
        print(f"  no icon for: {', '.join(missing)}")
    print(f"  {done}/{len(proj['codes'])} entries given an icon from {ICONS.relative_to(ROOT)}")

    if args.dry_run:
        print("  --dry-run: nothing written")
        return 0

    RHPROJ.write_text(json.dumps(proj, indent=2) + "\n")
    print(f"  wrote {RHPROJ.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
