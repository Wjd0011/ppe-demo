# -*- coding: utf-8 -*-
"""A/B experiment: whole-image inference vs tiled (sliding-window) inference.

A  = the baseline: the whole frame is letterboxed to 640x640 and inferred once.
B  = the change: the frame is cut into N x N overlapping tiles, each tile is
     letterboxed to 640x640 and inferred, boxes are mapped back to the original
     frame and merged with a class-aware NMS.

Everything else is held fixed: same ONNX graph, same weights, same
conf/iou thresholds, same test split, same evaluation code (eval_vs_gt).

Outputs out/ab_tiled.json with, for each mode:
    mAP50 / mAP50-95 / per-class AP / operating point P-R-F1
    recall by object size (small / medium / large) at conf 0.35
    detections per image, zero-detection ratio, latency ms/img

Usage:
    python tools/ab_tiled.py --split test [--tiles 2 3]
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

from eval_vs_gt import GT_CLASSES, MAP_MODEL_TO_GT, evaluate, iou_matrix, load_gt  # noqa: E402
from yolo_onnx_predict import imread_unicode, nms  # noqa: E402

# GT class index -> the model class id that should detect it
GT_TO_MODEL = {v: k for k, v in MAP_MODEL_TO_GT.items() if v is not None}

# object size buckets on sqrt(area) in pixels of the ORIGINAL frame
SIZE_BUCKETS = [(0, 48), (48, 96), (96, 10 ** 9)]
SIZE_NAMES = ["小 (<48px)", "中 (48-96px)", "大 (>=96px)"]


def tile_origins(total, tile, overlap):
    """Offsets that cover [0, total) with `tile`-sized windows and `overlap`."""
    if tile >= total:
        return [0]
    step = max(1, int(round(tile * (1.0 - overlap))))
    xs = list(range(0, total - tile + 1, step))
    if xs[-1] != total - tile:
        xs.append(total - tile)
    return xs


def detect_tiled(predictor, img, n, overlap):
    """Run the baseline detector on n x n overlapping tiles and merge."""
    h, w = img.shape[:2]
    tw = int(np.ceil(w / (1.0 + (n - 1) * (1.0 - overlap))))
    th = int(np.ceil(h / (1.0 + (n - 1) * (1.0 - overlap))))
    tw, th = min(tw, w), min(th, h)

    per_class = {}
    for y in tile_origins(h, th, overlap):
        for x in tile_origins(w, tw, overlap):
            crop = img[y:y + th, x:x + tw]
            if crop.size == 0:
                continue
            for d in predictor.detect(crop):
                b = list(d["xyxy"])
                b[0] += x
                b[2] += x
                b[1] += y
                b[3] += y
                per_class.setdefault(d["cls_id"], []).append(
                    (b, d["score"], d["cls_id"], d["name"])
                )

    merged = []
    for cid, items in per_class.items():
        boxes = np.array([it[0] for it in items], dtype=np.float64)
        scores = np.array([it[1] for it in items], dtype=np.float64)
        for i in nms(boxes, scores, predictor.iou):
            b, s, c, name = items[i]
            # clip to the frame
            b = [
                float(min(max(b[0], 0), w - 1)),
                float(min(max(b[1], 0), h - 1)),
                float(min(max(b[2], 0), w - 1)),
                float(min(max(b[3], 0), h - 1)),
            ]
            merged.append(
                {"xyxy": b, "score": float(s), "cls_id": int(c), "name": name}
            )
    return merged


def detect_multiscale(predictor, img, scales):
    """B3: same graph, but the frame is shrunk before the 640 letterbox.

    The ONNX graph is fixed at 640x640, so "放大" is impossible; shrinking the
    frame first raises the pixels-per-object ratio (a far-away worker becomes
    bigger inside the 640 tile). It is the realistic option for a fixed-size
    export and it costs nothing in latency.
    """
    h, w = img.shape[:2]
    per_class = {}
    for s in scales:
        if s == 1.0:
            view, fx, fy = img, 1.0, 1.0
        else:
            view = cv2.resize(
                img, (int(round(w * s)), int(round(h * s))),
                interpolation=cv2.INTER_AREA,
            )
            fy, fx = h / float(view.shape[0]), w / float(view.shape[1])
        for d in predictor.detect(view):
            b = list(d["xyxy"])
            b = [b[0] * fx, b[1] * fy, b[2] * fx, b[3] * fy]
            per_class.setdefault(d["cls_id"], []).append(
                (b, d["score"], d["cls_id"], d["name"])
            )

    merged = []
    for cid, items in per_class.items():
        boxes = np.array([it[0] for it in items], dtype=np.float64)
        scores = np.array([it[1] for it in items], dtype=np.float64)
        for i in nms(boxes, scores, predictor.iou):
            b, s2, c, name = items[i]
            merged.append(
                {"xyxy": [float(v) for v in b], "score": float(s2),
                 "cls_id": int(c), "name": name}
            )
    return merged


def detect_flip_tta(predictor, img):
    """B2: horizontal-flip test-time augmentation, merged by class-aware NMS."""
    h, w = img.shape[:2]
    items = []
    for view, flipped in ((img, False), (cv2.flip(img, 1), True)):
        for d in predictor.detect(view):
            b = list(d["xyxy"])
            if flipped:
                b = [w - 1 - b[2], b[1], w - 1 - b[0], b[3]]
            items.append((b, d["score"], d["cls_id"], d["name"]))

    per_class = {}
    for b, s, c, name in items:
        per_class.setdefault(c, []).append((b, s, c, name))
    merged = []
    for cid, group in per_class.items():
        boxes = np.array([it[0] for it in group], dtype=np.float64)
        scores = np.array([it[1] for it in group], dtype=np.float64)
        for i in nms(boxes, scores, predictor.iou):
            b, s, c, name = group[i]
            merged.append(
                {"xyxy": [float(v) for v in b], "score": float(s),
                 "cls_id": int(c), "name": name}
            )
    return merged


def recall_by_size(preds_json, gt_dir, img_dir, conf=0.35, iou_thr=0.5):
    """Per size bucket: how many GT boxes get matched at conf >= 0.35."""
    hit = np.zeros(len(SIZE_BUCKETS), dtype=np.int64)
    tot = np.zeros(len(SIZE_BUCKETS), dtype=np.int64)
    for name, payload in preds_json.items():
        stem = os.path.splitext(name)[0]
        img = imread_unicode(os.path.join(img_dir, name))
        if img is None:
            continue
        h, w = img.shape[:2]
        gts = load_gt(os.path.join(gt_dir, stem + ".txt"), w, h)
        if not gts:
            continue
        dets = [d for d in payload["detections"] if d["score"] >= conf]
        used = set()
        # match in descending score order, same rule as eval_vs_gt
        for d in sorted(dets, key=lambda t: -t["score"]):
            gc = MAP_MODEL_TO_GT.get(int(d["cls_id"]))
            if gc is None:
                continue
            best, bi = 0.0, -1
            for j, (c, box) in enumerate(gts):
                if j in used or c != gc:
                    continue
                v = float(iou_matrix(np.array(d["xyxy"])[None, :], box[None, :])[0, 0])
                if v > best:
                    best, bi = v, j
            if best >= iou_thr:
                used.add(bi)
        for j, (c, box) in enumerate(gts):
            side = float(np.sqrt(max(0.0, (box[2] - box[0]) * (box[3] - box[1]))))
            for k, (lo, hi) in enumerate(SIZE_BUCKETS):
                if lo <= side < hi:
                    tot[k] += 1
                    if j in used:
                        hit[k] += 1
                    break
    return {
        SIZE_NAMES[k]: {
            "gt": int(tot[k]),
            "hit": int(hit[k]),
            "recall": round(float(hit[k]) / tot[k], 4) if tot[k] else None,
        }
        for k in range(len(SIZE_BUCKETS))
    }


def run_mode(predictor, files, img_dir, mode, n, overlap, tta=False):
    from yolo_onnx_predict import PPEPredictor  # noqa: F401  (typing only)

    preds = {}
    t0 = time.time()
    empty = 0
    total = 0
    for name in files:
        img = imread_unicode(os.path.join(img_dir, name))
        if img is None:
            continue
        if tta:
            dets = detect_flip_tta(predictor, img)
        else:
            dets = predictor.detect(img) if mode == "A" else detect_tiled(
                predictor, img, n, overlap
            )
        preds[name] = {"detections": dets, "stats": {}}
        total += len(dets)
        if not dets:
            empty += 1
    dt = time.time() - t0
    return preds, dt / max(1, len(files)) * 1000.0, total, empty


def run_variant(predictor, files, img_dir, fn):
    preds = {}
    t0 = time.time()
    empty = 0
    total = 0
    for name in files:
        img = imread_unicode(os.path.join(img_dir, name))
        if img is None:
            continue
        dets = fn(predictor, img)
        preds[name] = {"detections": dets, "stats": {}}
        total += len(dets)
        if not dets:
            empty += 1
    dt = time.time() - t0
    return preds, dt / max(1, len(files)) * 1000.0, total, empty


def per_image_errors(preds, gt_dir, img_dir, conf=0.35, iou_thr=0.5):
    """Per image: TP / FP / FN plus which classes were missed."""
    out = []
    for name, payload in preds.items():
        stem = os.path.splitext(name)[0]
        img = imread_unicode(os.path.join(img_dir, name))
        if img is None:
            continue
        h, w = img.shape[:2]
        gts = load_gt(os.path.join(gt_dir, stem + ".txt"), w, h)
        dets = [d for d in payload["detections"] if d["score"] >= conf]
        used = set()
        tp = 0
        for d in sorted(dets, key=lambda t: -t["score"]):
            gc = MAP_MODEL_TO_GT.get(int(d["cls_id"]))
            if gc is None:
                continue
            best, bi = 0.0, -1
            for j, (c, box) in enumerate(gts):
                if j in used or c != gc:
                    continue
                v = float(iou_matrix(np.array(d["xyxy"])[None, :], box[None, :])[0, 0])
                if v > best:
                    best, bi = v, j
            if best >= iou_thr:
                used.add(bi)
                tp += 1
        fp = len(dets) - tp
        missed = [GT_CLASSES[c] for j, (c, _) in enumerate(gts) if j not in used]
        out.append(
            {
                "file": name,
                "tp": tp,
                "fp": fp,
                "fn": len(missed),
                "missed": missed,
                "det": len(dets),
                "gt": len(gts),
            }
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--iou", type=float, default=0.45)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "ab_tiled.json"))
    args = ap.parse_args()

    from yolo_onnx_predict import PPEPredictor

    img_dir = os.path.join(ROOT, args.split, "images")
    gt_dir = os.path.join(ROOT, args.split, "labels")
    files = sorted(
        f for f in os.listdir(img_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if args.limit:
        files = files[: args.limit]

    predictor = PPEPredictor(conf=args.conf, iou=args.iou)

    # A = baseline (whole frame, one 640 pass)
    # B = the promoted change (shrink the frame first, two scales)
    # C = the negative control (2x2 tiles) -- kept on purpose, it shows why
    #     naive tiling hurts a 640-fixed export
    plan = [
        ("A 整图基线", lambda p, img: p.detect(img), "一片 640 整图推理"),
        ("B 缩图多尺度", lambda p, img: detect_multiscale(p, img, [1.0, 0.5]),
         "先缩到 0.5 倍再进 640，与原尺度结果按类内 NMS 合并"),
        ("C 分块2x2", lambda p, img: detect_tiled(p, img, 2, 0.2),
         "切成 2x2 重叠块分别推理再合并（负面对照）"),
    ]

    report = {"split": args.split, "images": len(files), "conf": args.conf,
              "iou": args.iou, "modes": {}}

    for label, fn, desc in plan:
        preds, ms, total, empty = run_variant(predictor, files, img_dir, fn)
        tag = label.split()[0]
        tmp = os.path.join(ROOT, "out", "ab_pred_%s_%s.json" % (tag, args.split))
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(preds, f, ensure_ascii=False)
        metrics = evaluate(tmp, gt_dir, img_dir)
        sizes = recall_by_size(preds, gt_dir, img_dir, conf=args.conf)
        errors = per_image_errors(preds, gt_dir, img_dir, conf=args.conf)
        worst = sorted(errors, key=lambda e: (-e["fn"], -e["fp"]))[:8]
        report["modes"][label] = {
            "desc": desc,
            "latency_ms": round(ms, 1),
            "detections": total,
            "det_per_image": round(total / max(1, len(files)), 2),
            "empty_frames": empty,
            "empty_ratio": round(empty / max(1, len(files)), 4),
            "metrics": metrics,
            "recall_by_size": sizes,
            "worst_images": worst,
        }
        print(
            "\n%-14s mAP50=%.4f  mAP50-95=%.4f  det/img=%.2f  zero=%.1f%%  %.0f ms/img"
            % (label, metrics["mAP50"], metrics["mAP50_95"],
               total / max(1, len(files)),
               100.0 * empty / max(1, len(files)), ms),
            flush=True,
        )
        print("   " + "  ".join(
            "%s=%.3f" % (k, v["ap50"]) for k, v in metrics["per_class"].items()))
        for k, v in sizes.items():
            print("   recall %-14s %s (%d/%d)" % (k, v["recall"], v["hit"], v["gt"]))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("\nwritten:", args.out)


if __name__ == "__main__":
    main()
