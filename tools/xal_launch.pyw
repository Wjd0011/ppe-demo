# -*- coding: utf-8 -*-
"""X-AnyLabeling launcher (console-less) that lands on this repo's demo folder.

Double-click friendly: build a desktop shortcut whose target is

    <pythonw.exe> "<repo>\\tools\\xal_launch.pyw"

It opens ``demo2/images`` (60 site photos with Chinese JSON annotations) so no
File > Open Dir step is needed. A path passed on the command line (dragging a
folder onto the shortcut) always wins; ``--blank`` opens an empty session.

X-AnyLabeling only accepts a path through ``--filename`` (a named option), so a
bare dropped path is rewritten here; otherwise the app exits with
"unrecognized arguments".

Kept path-free on purpose: DEMO_DIR is derived from this file's location, so the
repository can be cloned anywhere.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_DIR = os.path.join(ROOT, "demo2", "images")


def main():
    try:
        from anylabeling.app import main as app_main
    except ImportError:
        sys.stderr.write(
            "X-AnyLabeling is not installed for this interpreter.\n"
            "  pip install \"x-anylabeling-cvhub[cpu]>=4.3.1\"\n"
        )
        return 2

    argv = list(sys.argv[1:])

    blank = bool(argv) and argv[0] == "--blank"
    if blank:
        argv = argv[1:]

    if argv:
        extra = argv                                   # dropped path
    elif blank:
        extra = []                                     # empty session
    elif os.path.isdir(DEMO_DIR):
        extra = [DEMO_DIR]                             # demo session
    else:
        extra = []

    if extra and not extra[0].startswith("-"):
        extra = ["--filename"] + extra
    # Always rebuild argv: leaving it untouched would forward our own flags
    # (e.g. --blank) to the app, which rejects unknown options and exits.
    sys.argv = [sys.argv[0]] + extra

    return app_main() or 0


if __name__ == "__main__":
    sys.exit(main())
