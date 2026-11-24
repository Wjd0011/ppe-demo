# -*- coding: utf-8 -*-
"""Standalone YOLOv8 ONNX inference for the PPE demo (no torch required).

Usage:
    python yolo_onnx_predict.py --images <dir> [--out <dir>] [--conf 0.35] [--iou 0.45]
                                [--save-yolo] [--labels-only]
"""
import argparse
import json
import os
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort

MODEL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_MODEL = os.path.join(MODEL_DIR, "models", "construction_ppe_yolov8n.onnx")

# Index order is authoritative: it comes from the model's labels.txt/data.yaml.
CLASSES = [
    "Hardhat",
    "Mask",
    "NO-Hardhat",
    "NO-Mask",
    "NO-Safety Vest",
    "Person",
    "Safety Cone",
    "Safety Vest",
    "machinery",
    "vehicle",
]

COLORS = {
    "Hardhat": (0, 200, 0),
    "Safety Vest": (0, 200, 0),
    "Person": (200, 160, 0),
    "Mask": (0, 200, 200),
    "NO-Hardhat": (0, 0, 255),
    "NO-Safety Vest": (0, 0, 255),
    "NO-Mask": (0, 0, 220),
    "Safety Cone": (0, 140, 255),
    "machinery": (150, 150, 150),
    "vehicle": (150, 150, 150),
}


def imread_unicode(path):
    """cv2.imread fails on non-ASCII paths on Windows; decode bytes instead."""
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_unicode(path, img):
    ext = os.path.splitext(path)[1] or ".jpg"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise IOError("encode failed: %s" % path)
    buf.tofile(path)


def letterbox(img, new_shape=640, color=(114, 114, 114)):
    h, w = img.shape[:2]
    r = min(new_shape / h, new_shape / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((new_shape, new_shape, 3), color, dtype=np.uint8)
    top = (new_shape - nh) // 2
    left = (new_shape - nw) // 2
    canvas[top : top + nh, left : left + nw] = resized
    return canvas, r, left, top


def nms(boxes, scores, iou_thres):
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[np.where(iou <= iou_thres)[0] + 1]
    return keep


class PPEPredictor:
    def __init__(self, model_path=DEFAULT_MODEL, conf=0.35, iou=0.45, imgsz=640):
        self.session = ort.InferenceSession(
            model_path, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz

    def detect(self, img):
        """Return list of dicts: {xyxy, score, cls_id, name}."""
        pad, ratio, dx, dy = letterbox(img, self.imgsz)
        blob = cv2.cvtColor(pad, cv2.COLOR_BGR2RGB)
        blob = blob.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        out = self.session.run(None, {self.input_name: blob})[0][0]  # (4+nc, 8400)

        cls_scores = out[4:, :]
        scores = cls_scores.max(axis=0)
        cls_ids = cls_scores.argmax(axis=0)
        mask = scores > self.conf
        if not mask.any():
            return []
        boxes_cxcywh = out[:4, mask].T
        scores = scores[mask]
        cls_ids = cls_ids[mask]

        # cxcywh (letterboxed space) -> xyxy in original image
        cx, cy, w, h = (
            boxes_cxcywh[:, 0],
            boxes_cxcywh[:, 1],
            boxes_cxcywh[:, 2],
            boxes_cxcywh[:, 3],
        )
        xyxy = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)
        xyxy[:, [0, 2]] = (xyxy[:, [0, 2]] - dx) / ratio
        xyxy[:, [1, 3]] = (xyxy[:, [1, 3]] - dy) / ratio
        ih, iw = img.shape[:2]
        xyxy[:, [0, 2]] = xyxy[:, [0, 2]].clip(0, iw - 1)
        xyxy[:, [1, 3]] = xyxy[:, [1, 3]].clip(0, ih - 1)

        keep = nms(xyxy, scores, self.iou)
        results = []
        for i in keep:
            cid = int(cls_ids[i])
            results.append(
                {
                    "xyxy": [float(v) for v in xyxy[i]],
                    "score": float(scores[i]),
                    "cls_id": cid,
                    "name": CLASSES[cid] if cid < len(CLASSES) else str(cid),
                }
            )
        return results


def draw(img, dets, show_score=True):
    out = img.copy()
    for d in dets:
        x1, y1, x2, y2 = [int(round(v)) for v in d["xyxy"]]
        color = COLORS.get(d["name"], (0, 255, 0))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        text = "%s %.2f" % (d["name"], d["score"]) if show_score else d["name"]
        (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(
            out,
            text,
            (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return out


def to_yolo_lines(dets, w, h):
    lines = []
    for d in dets:
        x1, y1, x2, y2 = d["xyxy"]
        cx = (x1 + x2) / 2.0 / w
        cy = (y1 + y2) / 2.0 / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        lines.append(
            "%d %.6f %.6f %.6f %.6f" % (d["cls_id"], cx, cy, bw, bh)
        )
    return lines


def compliance(dets):
    """Simple rule engine: a person is compliant when both a Hardhat and a
    Safety Vest overlap their box."""
    persons = [d for d in dets if d["name"] == "Person"]
    hats = [d for d in dets if d["name"] == "Hardhat"]
    vests = [d for d in dets if d["name"] == "Safety Vest"]

    def overlaps(a, b):
        ax1, ay1, ax2, ay2 = a["xyxy"]
        bx1, by1, bx2, by2 = b["xyxy"]
        ix = max(0.0, min(ax2, bx2) - max(ax1, bx1))
        iy = max(0.0, min(ay2, by2) - max(ay1, by1))
        inter = ix * iy
        if inter <= 0:
            return False
        bx_area = max(1e-9, (bx2 - bx1) * (by2 - by1))
        # the PPE box should sit mostly inside the person box
        return inter / bx_area > 0.25

    stats = {
        "person": len(persons),
        "with_helmet": 0,
        "with_vest": 0,
        "compliant": 0,
        "violations": [],
    }
    for i, p in enumerate(persons):
        has_hat = any(overlaps(p, h) for h in hats)
        has_vest = any(overlaps(p, v) for v in vests)
        stats["with_helmet"] += int(has_hat)
        stats["with_vest"] += int(has_vest)
        if has_hat and has_vest:
            stats["compliant"] += 1
        else:
            missing = []
            if not has_hat:
                missing.append("安全帽")
            if not has_vest:
                missing.append("反光背心")
            stats["violations"].append(
                {
                    "person_index": i,
                    "xyxy": p["xyxy"],
                    "missing": missing,
                }
            )
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, help="image directory")
    ap.add_argument("--out", default=None, help="output directory")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--iou", type=float, default=0.45)
    ap.add_argument("--save-yolo", action="store_true", help="write YOLO txt")
    ap.add_argument("--json", default=None, help="write detections json")
    ap.add_argument("--save-vis", action="store_true", help="also write the drawn overlays")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    out_dir = args.out or os.path.join(MODEL_DIR, "out", "pred")
    os.makedirs(out_dir, exist_ok=True)
    label_dir = os.path.join(out_dir, "labels")
    if args.save_yolo:
        os.makedirs(label_dir, exist_ok=True)

    files = sorted(
        f
        for f in os.listdir(args.images)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp"))
    )
    if args.limit:
        files = files[: args.limit]
    if not files:
        print("no images in", args.images)
        return 1

    pred = PPEPredictor(args.model, args.conf, args.iou)
    all_json = {}
    t0 = time.time()
    total_dets = 0
    for i, name in enumerate(files, 1):
        path = os.path.join(args.images, name)
        img = imread_unicode(path)
        if img is None:
            print("skip unreadable:", name)
            continue
        dets = pred.detect(img)
        total_dets += len(dets)
        stats = compliance(dets)
        if args.save_vis:
            vis = draw(img, dets)
            # badge with the violation count
            label = "Person %d | Compliant %d | Violation %d" % (
                stats["person"],
                stats["compliant"],
                len(stats["violations"]),
            )
            cv2.rectangle(vis, (0, 0), (min(vis.shape[1], 520), 30), (30, 30, 30), -1)
            cv2.putText(
                vis, label, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (0, 255, 120), 1, cv2.LINE_AA,
            )
            imwrite_unicode(os.path.join(out_dir, name), vis)
        if args.save_yolo:
            h, w = img.shape[:2]
            with open(
                os.path.join(label_dir, os.path.splitext(name)[0] + ".txt"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write("\n".join(to_yolo_lines(dets, w, h)))
        all_json[name] = {"detections": dets, "stats": stats}
        if i % 20 == 0 or i == len(files):
            print("%d/%d" % (i, len(files)), flush=True)

    dt = time.time() - t0
    print(
        "done: %d images, %d detections, %.0f ms/img"
        % (len(files), total_dets, dt / max(1, len(files)) * 1000)
    )
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(all_json, f, ensure_ascii=False, indent=1)
        print("json ->", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
