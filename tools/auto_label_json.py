# -*- coding: utf-8 -*-
"""Run X-AnyLabeling's own auto-labeling model over a folder and write its
native JSON annotation files (.json next to the image).

This is the same code path the GUI uses (Ctrl+A -> save), so the result opens
in X-AnyLabeling exactly as if it had been hand-annotated there.
"""
import argparse
import json
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 可选：X-AnyLabeling 装在别的 venv 里时，用环境变量指过去；装在当前解释器里就不用设
_extra = os.environ.get("XAL_SITE_PACKAGES")
if _extra:
    sys.path.insert(0, _extra)

import numpy as np
import cv2
from PyQt6.QtCore import QCoreApplication

import anylabeling.config as cfgmod

# X-AnyLabeling 的配置默认在用户目录；可用 XAL_CONFIG 覆盖
cfgmod.current_config_file = os.environ.get(
    "XAL_CONFIG", os.path.join(os.path.expanduser("~"), ".xanylabelingrc")
)

from anylabeling.services.auto_labeling.model import load_model_config
from anylabeling.services.auto_labeling.yolov8 import YOLOv8
from anylabeling.views.labeling.label_file import LabelFile

DEFAULT_CFG = os.path.join(ROOT, "models", "ppe_yolov8n.yaml")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=DEFAULT_CFG)
    ap.add_argument("--images", default=os.path.join(ROOT, "demo", "images"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--summary", default=os.path.join(ROOT, "out", "autolabel_summary.json"))
    args = ap.parse_args()

    app = QCoreApplication(sys.argv)  # noqa: F841 (Qt event context)

    cfg = load_model_config(open(args.config, encoding="utf-8"))
    model = YOLOv8(cfg, lambda msg: None)
    print("model:", cfg["display_name"], "| conf", model.conf_thres, "| iou", model.iou_thres)

    files = sorted(
        f for f in os.listdir(args.images)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if args.limit:
        files = files[: args.limit]

    summary = {}
    t0 = time.time()
    total = 0
    for i, fn in enumerate(files, 1):
        path = os.path.join(args.images, fn)
        img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print("skip:", fn)
            continue
        h, w = img.shape[:2]
        result = model.predict_shapes(img, path)
        shapes = result.shapes

        payload = {
            "version": "4.3.1",
            "flags": {},
            "shapes": [],
            "imagePath": fn,
            "imageData": None,
            "imageHeight": h,
            "imageWidth": w,
            "description": "auto-labeled with ppe_construction_yolov8n (X-AnyLabeling 4.3.1)",
        }
        for s in shapes:
            pts = [[round(p.x(), 2), round(p.y(), 2)] for p in s.points]
            payload["shapes"].append(
                {
                    "label": s.label,
                    "score": round(float(s.score) if s.score is not None else 0.0, 4),
                    "points": pts,
                    "group_id": None,
                    "description": "",
                    "difficult": False,
                    "shape_type": "rectangle",
                    "flags": {},
                    "attributes": {},
                }
            )

        out_json = os.path.join(args.images, os.path.splitext(fn)[0] + ".json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        labels = {}
        for s in shapes:
            labels[s.label] = labels.get(s.label, 0) + 1
        summary[fn] = {"count": len(shapes), "labels": labels, "size": [w, h]}
        total += len(shapes)
        if i % 10 == 0 or i == len(files):
            print("%d/%d" % (i, len(files)), flush=True)

    dt = time.time() - t0
    os.makedirs(os.path.dirname(args.summary), exist_ok=True)
    with open(args.summary, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(
        "done: %d images, %d boxes, %.0f ms/img" % (len(files), total, dt / max(1, len(files)) * 1000)
    )
    print("json annotations written next to each image in", args.images)


if __name__ == "__main__":
    main()
