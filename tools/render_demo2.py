# -*- coding: utf-8 -*-
"""Render the expanded demo set (demo2) as a three-view gallery.

Not part of `run.py --all` any more: the web page now ships a single gallery.
Kept so the 60-image extended set can still be rendered on demand.

Reuses the drawing/matching helpers from render_demo.py so the visual style is
identical to the first gallery.
"""
import argparse
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from render_demo import (  # noqa: E402
    ASSETS,
    GT_CLASSES,
    GT_CN,
    GT_COLORS,
    imread,
    imwrite,
    draw_boxes,
    load_gt,
    load_pred,
    match,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", default=os.path.join(ROOT, "demo2"))
    ap.add_argument("--assets", default=os.path.join(ROOT, "web", "assets2"))
    ap.add_argument("--stats", default=os.path.join(ROOT, "out", "demo2_stats.json"))
    args = ap.parse_args()

    img_dir = os.path.join(args.demo, "images")
    lbl_dir = os.path.join(args.demo, "labels")
    os.makedirs(args.assets, exist_ok=True)

    files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".jpg"))
    stats = []
    for fn in files:
        stem = os.path.splitext(fn)[0]
        img = imread(os.path.join(img_dir, fn))
        if img is None:
            print("unreadable:", fn)
            continue
        h, w = img.shape[:2]
        gts = load_gt(stem, w, h, lbl_dir)
        preds = load_pred(stem, img_dir)
        tp, fp, fns = match(preds, gts)

        imwrite(os.path.join(args.assets, "orig_%s.jpg" % stem), img)
        imwrite(
            os.path.join(args.assets, "gt_%s.jpg" % stem),
            draw_boxes(img, [(c, b, GT_COLORS[c], GT_CN[c]) for c, b in gts]),
        )
        items = []
        for label, box, score, mapped in preds:
            if mapped is None:
                continue
            items.append((label, box, GT_COLORS[mapped], "%s %.2f" % (GT_CN[mapped], score)))
        imwrite(os.path.join(args.assets, "pred_%s.jpg" % stem), draw_boxes(img, items))

        cnt = collections.Counter(c for c, _ in gts)
        stats.append(
            {
                "file": fn,
                "stem": stem,
                "size": [w, h],
                "gt": {GT_CN[k]: v for k, v in cnt.items()},
                "gt_total": len(gts),
                "pred_total": len(items),
                "tp": len(tp),
                "fp": len(fp),
                "fn": len(fns),
                "fn_classes": dict(collections.Counter(c for c, _ in fns)),
                "fp_classes": dict(collections.Counter(c for c, _ in fp)),
            }
        )

    os.makedirs(os.path.dirname(args.stats), exist_ok=True)
    with open(args.stats, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)

    tp = sum(s["tp"] for s in stats)
    fp = sum(s["fp"] for s in stats)
    fn = sum(s["fn"] for s in stats)
    print(
        "rendered %d images | TP %d FP %d FN %d | P %.3f R %.3f"
        % (len(stats), tp, fp, fn, tp / max(1, tp + fp), tp / max(1, tp + fn))
    )
    print("assets ->", args.assets)


if __name__ == "__main__":
    main()
