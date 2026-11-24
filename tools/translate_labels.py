"""Translate the already-generated X-AnyLabeling JSON annotations to Chinese.

The model config now emits Chinese class names, so every auto-generated JSON
must match it, otherwise the label list shows both English and Chinese entries
for the same class.

Usage:
    python translate_labels.py --dirs demo/images demo2/images [--write]

Without --write it only reports what would change (dry run).
"""
import argparse
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 10 model classes, index order == ONNX output channel order.
EN_TO_CN = {
    "Hardhat": "安全帽",
    "Mask": "口罩",
    "NO-Hardhat": "未戴安全帽",
    "NO-Mask": "未戴口罩",
    "NO-Safety Vest": "未穿反光背心",
    "Person": "人",
    "Safety Cone": "锥桶",
    "Safety Vest": "反光背心",
    "machinery": "机械",
    "vehicle": "车辆",
}

# Class-name colours are derived from the label string in X-AnyLabeling, so
# translated labels simply get a new (stable) colour. Nothing to remap here.

DESC = "模型自动标注（X-AnyLabeling 4.3.1 / PPE YOLOv8n）"


def translate_file(path, write):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    changed = 0
    for shape in data.get("shapes") or []:
        en = shape.get("label")
        if en in EN_TO_CN and EN_TO_CN[en] != en:
            shape["label"] = EN_TO_CN[en]
            changed += 1
    unknown = sorted(
        {
            s.get("label")
            for s in data.get("shapes") or []
            if s.get("label") not in EN_TO_CN.values()
        }
    )
    if write and changed:
        data["description"] = DESC
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return changed, len(data.get("shapes") or []), unknown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", default=["demo/images", "demo2/images"])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    total_files = total_boxes = total_unknown = 0
    for rel in args.dirs:
        d = os.path.join(ROOT, rel)
        files = sorted(glob.glob(os.path.join(d, "*.json")))
        n_boxes = n_changed = 0
        for p in files:
            changed, n, unknown = translate_file(p, args.write)
            n_boxes += n
            n_changed += changed
            if unknown:
                total_unknown += 1
                print("  ! unknown labels in", os.path.basename(p), unknown)
        print(
            "%-16s files %3d  boxes %4d  translated %4d  %s"
            % (rel, len(files), n_boxes, n_changed, "written" if args.write else "dry-run")
        )
        total_files += len(files)
        total_boxes += n_boxes
    print("total files %d  boxes %d  files-with-unknown %d" % (total_files, total_boxes, total_unknown))


if __name__ == "__main__":
    main()
