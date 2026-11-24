"""Keep only the PPE classes this demo reports on.

The model outputs 10 channels (that order is fixed by the ONNX graph), but the
classroom demo only reports 5 of them: whether each person wears a hard hat and
a high-visibility vest. Everything else (mask, cone, machinery, vehicle, ...) is
dropped from the annotations so the label list stays clean.

Usage:
    python prune_labels.py --dirs demo/images demo2/images [--write]

Without --write it only reports what would be removed.
"""
import argparse
import collections
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The five labels that survive.
KEEP = ["安全帽", "未戴安全帽", "反光背心", "未穿反光背心", "人"]

DESC = "模型自动标注（X-AnyLabeling 4.3.1 / PPE YOLOv8n，仅保留安全帽与反光背心相关类别）"


def prune_file(path, write):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    shapes = data.get("shapes") or []
    kept = [s for s in shapes if s.get("label") in KEEP]
    dropped = collections.Counter(
        s.get("label") for s in shapes if s.get("label") not in KEEP
    )
    if write and len(kept) != len(shapes):
        data["shapes"] = kept
        data["description"] = DESC
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return len(shapes), len(kept), dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", default=["demo/images", "demo2/images"])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    removed = collections.Counter()
    before = after = files = 0
    for rel in args.dirs:
        d = os.path.join(ROOT, rel)
        fs = sorted(glob.glob(os.path.join(d, "*.json")))
        fb = fa = 0
        for p in fs:
            b, a, dropped = prune_file(p, args.write)
            fb += b
            fa += a
            removed.update(dropped)
        print(
            "%-16s files %3d  boxes %4d -> %4d  removed %4d"
            % (rel, len(fs), fb, fa, fb - fa)
        )
        files += len(fs)
        before += fb
        after += fa
    print("total files %d  boxes %d -> %d  (%s)"
          % (files, before, after, "written" if args.write else "dry-run"))
    if removed:
        print("removed by class:")
        for k, v in removed.most_common():
            print("  %-10s %4d" % (k, v))


if __name__ == "__main__":
    main()
