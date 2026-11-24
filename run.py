# -*- coding: utf-8 -*-
"""One entry point that reproduces every number on the web page.

    python run.py --all            # everything below, in order
    python run.py --infer          # 1) run the ONNX model over the test split
    python run.py --eval           # 2) compare against ground truth -> mAP/P/R
    python run.py --ab             # 3) A/B: whole-image vs multi-scale vs tiled
    python run.py --painting       # 4) re-render the demo gallery's three-view images
    python run.py --failures       # 5) pick + render the worst cases
    python run.py --web            # 6) rebuild web/index.html from out/*.json
    python run.py --gui            # 7) open the labelling demo in X-AnyLabeling

Every step shells out to the corresponding script in tools/, so the numbers on
the page can always be traced back to a command that was actually run.

Notes
-----
* The model is a plain .onnx file: no torch and no CUDA are required.
* Colours / paths use non-ASCII directory names; every image is read with
  ``cv2.imdecode(np.fromfile(...))`` because ``cv2.imread`` cannot open such
  paths on Windows. This is handled inside the tools, not here.
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(ROOT, "tools")
PY = sys.executable

STEPS = {
    "infer": [
        ("infer test split", ["tools/yolo_onnx_predict.py",
                              "--images", "test/images",
                              "--out", "out/pred",
                              "--json", "out/pred_test.json"]),
    ],
    "painting": [
        ("render demo gallery", ["tools/render_demo.py"]),
    ],
    "eval": [
        ("evaluate all three splits", ["tools/run_full_eval.py",
                                        "--splits", "valid,test,train"]),
    ],
    "ab": [
        ("A/B on test", ["tools/ab_tiled.py", "--split", "test"]),
        ("A/B on valid", ["tools/ab_tiled.py", "--split", "valid",
                          "--out", "out/ab_tiled_valid.json"]),
    ],
    "failures": [
        ("worst-case gallery", ["tools/render_failures.py", "--top", "6",
                                "--pred", "out/pred_test.json"]),
    ],
    "web": [
        ("rebuild the page", ["tools/build_web.py"]),
    ],
}

ORDER = ["infer", "eval", "ab", "painting", "failures", "web"]


def run_one(title, argv):
    print("\n=== %s ===" % title)
    print("$ python " + " ".join(argv))
    t0 = time.time()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run([PY] + argv, cwd=ROOT, env=env)
    dt = time.time() - t0
    if proc.returncode != 0:
        print("FAILED (%d) after %.1fs" % (proc.returncode, dt))
        return False
    print("ok (%.1fs)" % dt)
    return True


def open_gui():
    """Launch X-AnyLabeling straight on the labelled demo photos.

    Order: (1) the repo's own launcher ``tools/xal_launch.pyw`` -- works on any
    machine that has X-AnyLabeling installed, no desktop shortcut needed;
    (2) a desktop shortcut, if the user happens to have made one.
    """
    launcher = os.path.join(TOOLS, "xal_launch.pyw")
    if os.path.isfile(launcher):
        print("opening:", launcher)
        subprocess.Popen(
            [PY, launcher],
            cwd=ROOT,
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
        return True
    lnk = os.path.join(os.path.expanduser("~"), "Desktop",
                       "X-AnyLabeling 标注演示.lnk")
    if os.path.isfile(lnk):
        print("opening:", lnk)
        os.startfile(lnk)  # noqa: S606 - Windows shell open
        return True
    print("launcher not found:", launcher)
    print("fallback:  xanylabeling  (then File > Open Dir on demo2/images)")
    return False


def main():
    ap = argparse.ArgumentParser(
        description="Reproduce the PPE demo end to end.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    for k in ORDER:
        ap.add_argument("--" + k, action="store_true")
    ap.add_argument("--all", action="store_true", help="run every step in order")
    ap.add_argument("--gui", action="store_true", help="open the labelling demo")
    args = ap.parse_args()

    chosen = [k for k in ORDER if getattr(args, k)]
    if args.all:
        chosen = list(ORDER)
    do_gui = args.gui

    if not chosen and not do_gui:
        ap.print_help()
        return 0

    failed = []
    for k in chosen:
        for title, argv in STEPS[k]:
            if not run_one(title, argv):
                failed.append(title)
                break          # a failed step makes the later ones meaningless

    if do_gui:
        open_gui()

    print("\n" + "=" * 56)
    if failed:
        print("FAILED:", "; ".join(failed))
        return 1
    print("all selected steps finished")
    print("page:", os.path.join(ROOT, "web", "index.html"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
