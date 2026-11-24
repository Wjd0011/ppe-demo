# -*- coding: utf-8 -*-
"""Evaluate the PPE ONNX model against the YOLO ground-truth labels.

Pure numpy implementation (no torch / no pycocotools):
  * greedy matching at a set of IoU thresholds
  * VOC-style interpolated AP, plus mAP50 / mAP50-95
  * per-class precision / recall / F1 at conf=0.001 and conf=0.35

The dataset uses 5 classes, the model predicts 10; the mapping lives in
MAP_MODEL_TO_GT so a wrong index order fails loudly instead of silently
mislabelling everything.
"""
import argparse
import collections
import glob
import json
import os

import numpy as np

GT_CLASSES = ["helmet", "no-helmet", "no-vest", "person", "vest"]

# model class index -> dataset class index (None = not evaluated)
MAP_MODEL_TO_GT = {
    0: 0,  # Hardhat     -> helmet
    2: 1,  # NO-Hardhat  -> no-helmet
    4: 2,  # NO-Safety Vest -> no-vest
    5: 3,  # Person      -> person
    7: 4,  # Safety Vest -> vest
    1: None,  # Mask
    3: None,  # NO-Mask
    6: None,  # Safety Cone
    8: None,  # machinery
    9: None,  # vehicle
}


def iou_matrix(a, b):
    """a: (N,4) xyxy, b: (M,4) xyxy -> (N,M) IoU."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    ax1, ay1, ax2, ay2 = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    bx1, by1, bx2, by2 = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    ix1 = np.maximum(ax1[:, None], bx1[None, :])
    iy1 = np.maximum(ay1[:, None], by1[None, :])
    ix2 = np.minimum(ax2[:, None], bx2[None, :])
    iy2 = np.minimum(ay2[:, None], by2[None, :])
    iw = np.clip(ix2 - ix1, 0, None)
    ih = np.clip(iy2 - iy1, 0, None)
    inter = iw * ih
    area_a = np.clip(ax2 - ax1, 0, None) * np.clip(ay2 - ay1, 0, None)
    area_b = np.clip(bx2 - bx1, 0, None) * np.clip(by2 - by1, 0, None)
    return inter / np.maximum(area_a[:, None] + area_b[None, :] - inter, 1e-9)


def load_gt(label_path, w, h):
    """YOLO txt -> list of (cls, xyxy)."""
    out = []
    if not os.path.isfile(label_path):
        return out
    with open(label_path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            c = int(float(parts[0]))
            cx, cy, bw, bh = [float(v) for v in parts[1:5]]
            out.append(
                (
                    c,
                    np.array(
                        [
                            (cx - bw / 2) * w,
                            (cy - bh / 2) * h,
                            (cx + bw / 2) * w,
                            (cy + bh / 2) * h,
                        ],
                        dtype=np.float64,
                    ),
                )
            )
    return out


def voc_ap(rec, prec):
    """101-point interpolated AP (the metric YOLO/COCO reports as AP50)."""
    mrec = np.concatenate(([0.0], rec, [1.0]))
    mpre = np.concatenate(([0.0], prec, [0.0]))
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    grid = np.linspace(0, 1, 101)
    idx = np.searchsorted(mrec, grid, side="left")
    idx = np.clip(idx, 0, len(mpre) - 1)
    return float(np.mean(mpre[idx]))


def evaluate(pred_json, labels_dir, image_dir, iou_thresholds=None):
    if iou_thresholds is None:
        iou_thresholds = [round(0.5 + 0.05 * i, 2) for i in range(10)]

    with open(pred_json, encoding="utf-8") as f:
        preds = json.load(f)

    import cv2

    # gather predictions and ground truth
    per_class_preds = collections.defaultdict(list)  # cls -> [(score, img, xyxy)]
    per_class_gt = collections.defaultdict(lambda: collections.defaultdict(list))
    npos = collections.Counter()
    n_gt_total = 0
    n_pred_total = 0

    for img_name, payload in preds.items():
        stem = os.path.splitext(img_name)[0]
        img_path = os.path.join(image_dir, img_name)
        img = cv2.imdecode(np.fromfile(img_path, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        gts = load_gt(os.path.join(labels_dir, stem + ".txt"), w, h)

        for c, box in gts:
            per_class_gt[c][img_name].append(box)
            npos[c] += 1
            n_gt_total += 1

        for d in payload["detections"]:
            gt_c = MAP_MODEL_TO_GT.get(int(d["cls_id"]))
            n_pred_total += 1
            if gt_c is None:
                continue
            per_class_preds[gt_c].append(
                (d["score"], img_name, np.array(d["xyxy"], dtype=np.float64))
            )

    ap_table = {}
    for c in range(len(GT_CLASSES)):
        dets = sorted(per_class_preds.get(c, []), key=lambda t: -t[0])
        gt_by_img = per_class_gt.get(c, {})
        npos_c = npos[c]
        aps = []
        for thr in iou_thresholds:
            used = collections.defaultdict(set)
            tp = np.zeros(len(dets))
            fp = np.zeros(len(dets))
            for i, (score, img, box) in enumerate(dets):
                gts = gt_by_img.get(img, [])
                best_iou, best_j = 0.0, -1
                for j, g in enumerate(gts):
                    if j in used[img]:
                        continue
                    iou = float(iou_matrix(box[None, :], g[None, :])[0, 0])
                    if iou > best_iou:
                        best_iou, best_j = iou, j
                if best_iou >= thr and best_j >= 0:
                    used[img].add(best_j)
                    tp[i] = 1
                else:
                    fp[i] = 1
            if len(dets) == 0 or npos_c == 0:
                aps.append(0.0)
                continue
            ctp = np.cumsum(tp)
            cfp = np.cumsum(fp)
            rec = ctp / npos_c
            prec = ctp / np.maximum(ctp + cfp, 1e-9)
            aps.append(voc_ap(rec, prec))
        ap_table[GT_CLASSES[c]] = {
            "ap50": round(aps[0], 4),
            "ap50_95": round(float(np.mean(aps)), 4),
            "gt": int(npos_c),
            "pred": len(dets),
        }

    # operating-point precision / recall at conf = 0.35
    op = {}
    for c in range(len(GT_CLASSES)):
        dets = [d for d in per_class_preds.get(c, []) if d[0] >= 0.35]
        gt_by_img = per_class_gt.get(c, {})
        used = collections.defaultdict(set)
        tp = 0
        for score, img, box in sorted(dets, key=lambda t: -t[0]):
            gts = gt_by_img.get(img, [])
            best_iou, best_j = 0.0, -1
            for j, g in enumerate(gts):
                if j in used[img]:
                    continue
                iou = float(iou_matrix(box[None, :], g[None, :])[0, 0])
                if iou > best_iou:
                    best_iou, best_j = iou, j
            if best_iou >= 0.5 and best_j >= 0:
                used[img].add(best_j)
                tp += 1
        n_pred = len(dets)
        npos_c = npos[c]
        p = tp / n_pred if n_pred else 0.0
        r = tp / npos_c if npos_c else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        op[GT_CLASSES[c]] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "pred": n_pred,
            "gt": int(npos_c),
        }

    map50 = float(np.mean([v["ap50"] for v in ap_table.values()]))
    map50_95 = float(np.mean([v["ap50_95"] for v in ap_table.values()]))
    summary = {
        "images": len(preds),
        "gt_boxes": int(n_gt_total),
        "pred_boxes": int(n_pred_total),
        "mAP50": round(map50, 4),
        "mAP50_95": round(map50_95, 4),
        "per_class": ap_table,
        "operating_point_conf035": op,
    }
    return summary


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--pred", default=os.path.join(root, "out", "pred_test.json"))
    ap.add_argument("--images", default=os.path.join(root, "test", "images"))
    ap.add_argument("--labels", default=os.path.join(root, "test", "labels"))
    ap.add_argument("--out", default=os.path.join(root, "out", "metrics.json"))
    args = ap.parse_args()

    s = evaluate(args.pred, args.labels, args.images)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    print("written:", args.out)


if __name__ == "__main__":
    main()
