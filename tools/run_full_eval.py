# -*- coding: utf-8 -*-
"""Run the model over every split of the construction-safety dataset and
evaluate each split plus the union.

Usage:
    python tools/run_full_eval.py [--splits train,valid,test] [--conf 0.35]

Outputs
    out/full_eval_summary.json   compact per-split table + the weighted union
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

from yolo_onnx_predict import PPEPredictor, imread_unicode  # noqa: E402
from eval_vs_gt import evaluate  # noqa: E402


def predict_split(pred, split, out_path, conf):
    img_dir = os.path.join(ROOT, split, "images")
    files = sorted(
        f for f in os.listdir(img_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    results = {}
    t0 = time.time()
    for i, fn in enumerate(files, 1):
        img = imread_unicode(os.path.join(img_dir, fn))
        if img is None:
            continue
        dets = pred.detect(img)
        results[fn] = {"detections": dets, "size": [img.shape[1], img.shape[0]]}
        if i % 100 == 0:
            print("  %s %d/%d" % (split, i, len(files)), flush=True)
    dt = time.time() - t0
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print("  %s: %d images, %.1f ms/img" % (split, len(results), dt / max(1, len(files)) * 1000))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="valid,test,train")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--iou", type=float, default=0.45)
    args = ap.parse_args()

    pred = PPEPredictor(
        os.path.join(ROOT, "models", "construction_ppe_yolov8n.onnx"),
        conf=args.conf,
        iou=args.iou,
    )

    out_dir = os.path.join(ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)

    summary = {}
    per_split = []
    for split in [s.strip() for s in args.splits.split(",") if s.strip()]:
        img_dir = os.path.join(ROOT, split, "images")
        lbl_dir = os.path.join(ROOT, split, "labels")
        if not os.path.isdir(img_dir):
            print("skip missing split:", split)
            continue
        pred_path = os.path.join(out_dir, "pred_%s.json" % split)
        res = predict_split(pred, split, pred_path, args.conf)
        del res
        m = evaluate(pred_path, lbl_dir, img_dir)
        per_split.append(m)
        summary[split] = {
            "images": m["images"],
            "gt_boxes": m["gt_boxes"],
            "pred_boxes": m["pred_boxes"],
            "mAP50": m["mAP50"],
            "mAP50_95": m["mAP50_95"],
            "per_class": {k: v["ap50"] for k, v in m["per_class"].items()},
        }
        print("  %s mAP50=%.4f mAP50-95=%.4f (%d imgs)" % (
            split, m["mAP50"], m["mAP50_95"], m["images"]))
        os.remove(pred_path)  # only needed while scoring this split

    if per_split:
        import eval_vs_gt as ev

        all_gt = sum(m["gt_boxes"] for m in per_split)
        all_pred = sum(m["pred_boxes"] for m in per_split)
        ap_pool = {c: [] for c in ev.GT_CLASSES}
        for m in per_split:
            for c, v in m["per_class"].items():
                ap_pool[c].append((v["ap50"], v["gt"]))
        weighted = {}
        for c, items in ap_pool.items():
            wsum = sum(v * n for v, n in items)
            ntot = sum(n for _, n in items)
            weighted[c] = round(wsum / ntot, 4) if ntot else 0.0
        summary["all"] = {
            "images": sum(s["images"] for s in summary.values()),
            "gt_boxes": all_gt,
            "pred_boxes": all_pred,
            "mAP50": round(float(np.mean(list(weighted.values()))), 4),
            "per_class_AP50_weighted": weighted,
        }

    with open(os.path.join(out_dir, "full_eval_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
