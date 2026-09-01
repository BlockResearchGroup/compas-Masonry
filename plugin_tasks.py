"""Build the installable Rhino package.

A port of resources/rui/build_plugin.sh to invoke, so the build runs the same way
on macOS and Windows. The shell script needs Git Bash on Windows and hardcodes
the macOS layout of Rhino's tools; this does not.

NEVER called by CI. It shells out to `rhinocode` and `yak`, which the runners do
not have. `tasks.py` is imported on 9 runners (3 OS x 3 Python), so everything at
module level here must stay stdlib + invoke.

Why this is not just `rhinocode project build`
----------------------------------------------
`rhinocode project build` always writes its OWN COMPAS-Masonry.rui at the package
root, and no flag suppresses it. That generated toolbar has no ordering and no
separators, because the .rhproj schema cannot express either -- a codes[] entry
carries only id, language, title, uri, image. The designed toolbar
(resources/COMPAS-Masonry.rui) therefore has to be copied over the generated one
AFTER the build and BEFORE `yak build` repackages, since `yak install --source`
reads the .yak and not the loose files beside it.

Getting that order wrong fails silently, and stays invisible on a machine where
resources/COMPAS-Masonry.rui is also registered by hand: both copies carry the
same pinned collection guid, so the toolbar looks right while the package ships
the generated one. The md5 assertion in step 6 is the only check that catches it.
"""

import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

from invoke import Exit
from invoke import task

# `8.*-windows` is accepted and silently produces a generic `rh8` build that
# claims no platform. The spelling Rhino actually recognises is `8.*-win`.
TARGETS = {
    "mac": ("8.*-macOS", "build/rh8-mac"),
    "win": ("8.*-win", "build/rh8-win"),
}

TOOLS = {
    "darwin": pathlib.Path("/Applications/Rhino 8.app/Contents/Resources/bin"),
    "win32": pathlib.Path(r"C:\Program Files\Rhino 8\System"),
}


def _platform():
    return "win" if sys.platform == "win32" else "mac"


def _tool(name):
    """Locate `rhinocode` or `yak`, preferring an explicit environment override.

    RHINOCODE and YAK are honoured separately rather than derived from one Rhino
    path: the two live in different directories per platform, so a single root
    only works on macOS.
    """
    override = os.environ.get(name.upper())
    if override:
        path = pathlib.Path(override)
    else:
        directory = TOOLS.get(sys.platform)
        if directory is None:
            raise Exit(f"no known Rhino layout for {sys.platform} -- set {name.upper()}")
        path = directory / (f"{name}.exe" if sys.platform == "win32" else name)
    if not path.exists():
        raise Exit(f"not found: {path}  (set {name.upper()} to override)")
    return str(path)


def _run(ctx, args, cwd=None):
    """Run a command as an argv list, so paths with spaces need no quoting.

    ctx.run() takes a shell string, which is exactly the wrong shape here:
    "/Applications/Rhino 8.app/..." would split on the space.
    """
    print("    $ " + " ".join(args))
    result = subprocess.run(args, cwd=cwd)
    if result.returncode != 0:
        raise Exit(f"failed ({result.returncode}): {args[0]}", code=result.returncode)


def _set_rhproj_version(rhproj, version):
    """Targeted text edit, not a JSON round-trip: the rhproj carries 28 base64
    SVGs and reserialising it would rewrite the whole file for one string."""
    text = rhproj.read_text()
    pattern = re.compile(r'("identity"\s*:\s*\{.*?"version"\s*:\s*")([^"]*)(")', re.S)
    match = pattern.search(text)
    if not match:
        raise Exit("could not find identity.version -- edit it by hand")
    print(f"    {match.group(2)} -> {version}")
    rhproj.write_text(pattern.sub(lambda m: m.group(1) + version + m.group(3), text, count=1))


def _assert_designed_rui(rui, builddir):
    """The build is only correct if the ARCHIVE carries the designed toolbar."""
    archives = sorted(builddir.glob("*.yak"))
    if len(archives) != 1:
        raise Exit(f"expected exactly one .yak in {builddir}, found {len(archives)}")

    mine = rui.read_bytes()
    inside = zipfile.ZipFile(archives[0]).read("COMPAS-Masonry.rui")
    guid = ET.fromstring(inside).get("guid")

    print(f"    repo : {hashlib.md5(mine).hexdigest()[:12]}  {len(mine)} bytes")
    print(f"    yak  : {hashlib.md5(inside).hexdigest()[:12]}  {len(inside)} bytes  guid {guid}")
    if mine != inside:
        raise Exit("    MISMATCH -- the archive carries the GENERATED toolbar, not yours")
    print("    MATCH")


@task(
    help={
        "version": "build version, e.g. 0.5.3-beta. Bump on EVERY rebuild -- Rhino keys packages by version and installs them side by side, so reusing one invites a stale load.",
        "regen-icons": (
            "redraw the artwork from resources/icons/ before building. Only needed when an SVG there changed; requires rsvg-convert. "
            "Without it the tracked resources/COMPAS-Masonry.rui is used as it stands, and step 2 still fails the build if it no longer matches."
        ),
        "bump-rhproj": "also write VERSION into COMPAS-Masonry.rhproj identity.version",
        "target": "'mac' or 'win' (default: this machine), or a literal rhinocode buildtarget",
        "builddir": "override the output directory implied by --target",
    }
)
def build_plugin(ctx, version, regen_icons=False, bump_rhproj=False, target=None, builddir=None):
    """Build the Rhino plugin with the DESIGNED toolbar, ready for `yak push`."""
    root = pathlib.Path(__file__).parent
    rui = root / "resources" / "COMPAS-Masonry.rui"
    rhproj = root / "COMPAS-Masonry.rhproj"

    key = target or _platform()
    if key in TARGETS:
        buildtarget, default_dir = TARGETS[key]
    else:
        buildtarget = key
        if builddir is None:
            raise Exit(f"--target {key} is not 'mac' or 'win', so --builddir is required")
        default_dir = builddir
    out = root / (builddir or default_dir)

    rhinocode, yak = _tool("rhinocode"), _tool("yak")

    print("==> 1/7  icon sheet and compiled RUI")
    if regen_icons:
        # Defaults reproduce the shipped look: the artwork AS DRAWN, --min-stroke
        # 0.6. To use different values, run make_icons.py by hand and omit
        # --regen-icons here.
        for script in ("set_rhproj_icons.py", "make_icons.py", "generate_rui.py"):
            _run(ctx, [sys.executable, str(root / "resources" / "rui" / script)])
    else:
        # Opt-in rather than opt-out: regenerating needs rsvg-convert installed
        # and rewrites three tracked files, which is the wrong price for a
        # release where the artwork did not change. Nothing is lost by defaulting
        # off -- step 2 compares the .rui against the artwork and fails the build
        # if they have diverged, so a forgotten --regen-icons is caught there
        # rather than shipping stale icons.
        print(f"    using {rui.name} as it stands (pass --regen-icons if the artwork changed)")

    print("==> 2/7  verify both icon systems")
    # Exits 1 on a missing icon, an out-of-range index, an unfilled button size,
    # or a .rui compiled from a different sheet -- all of which would otherwise
    # only surface as "my icons did not update" after an install.
    _run(ctx, [sys.executable, str(root / "resources" / "rui" / "verify_icons.py")])

    if bump_rhproj:
        print(f"==> 2b/7  set identity.version in {rhproj.name} to {version}")
        _set_rhproj_version(rhproj, version)

    print(f"==> 3/7  clear {root / 'build'}")
    # Not optional: setuptools uses the same directory when the sync scripts
    # pip-install the package, and it never prunes -- stale modules have survived
    # a build this way.
    shutil.rmtree(root / "build", ignore_errors=True)

    print(f"==> 4/7  rhinocode project build ({version}, target {buildtarget})")
    _run(ctx, [rhinocode, "project", "build", str(rhproj), "--buildversion", version, "--buildtarget", buildtarget])
    if not out.is_dir():
        raise Exit(f"expected {out} -- wrong --target/--builddir?")

    print("==> 5/7  swap in the designed RUI")
    shutil.copyfile(rui, out / "COMPAS-Masonry.rui")

    print("==> 6/7  repackage and assert the archive carries it")
    # `rhinocode project build` ALREADY wrote a .yak containing the generated
    # toolbar, under a different filename than the one `yak build` writes. Both
    # declare the same version, so leaving them side by side makes
    # `yak install --source <dir>` pick between two archives on undocumented
    # grounds. Delete first so there is nothing to choose between.
    for stale in out.glob("*.yak"):
        stale.unlink()
    # `yak build` needs the platform the package is FOR and does not read
    # --buildtarget, so a mismatch here stamps a Windows build as a mac package.
    platform = "win" if "win" in buildtarget else "mac" if "mac" in buildtarget.lower() else "any"
    print(f"    packaging for platform: {platform}  (from target {buildtarget})")
    _run(ctx, [yak, "build", "--platform", platform], cwd=str(out))
    _assert_designed_rui(rui, out)

    print("==> 7/7  install command")
    # The build stamps its own +<build> suffix, so this is neither the string
    # passed to --buildversion nor the one in the .yak filename. A wrong version
    # gives "[error] No package found by the name of...", which reads like a
    # network failure.
    match = re.search(r"^version:\s*(\S+)", (out / "manifest.yml").read_text(), re.M)
    if not match:
        raise Exit("no version in manifest.yml")

    print(f"""
Package ready: {out}
Toolbar in it: yours ({rui.relative_to(root)})

QUIT RHINO, then:

  "{yak}" install --source "{out}" COMPAS-Masonry {match.group(1)}

Then confirm the package carries the commands in the repo -- a version bump
proves a build happened, not what went into it, and Rhino keeps older versions
on disk beside the new one:

  python resources/rui/verify_install.py

Rhino registers the packaged RUI by PATH, and does not update that registration
when the version changes: after installing, the toolbar is missing until you
open it once from Tools > Toolbar Layout > File > Open:

  {out / "COMPAS-Masonry.rui"}
""")
