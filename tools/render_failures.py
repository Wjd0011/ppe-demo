# -*- coding: utf-8 -*-
"""Render the failure-case gallery: the test images the model handles worst.

For each image it writes:
    web/assets3/orig_<stem>.jpg   the raw frame
    web/assets3/pred_<stem>.jpg   the model overlay (green = matched, red = FP,
                                  dashed orange = missed GT)
and a row in out/failure_stats.json with data-driven reasons:
    * how many GT boxes were missed, per class, and their size mix
    * how many false positives, per class
    * a one-line diagnosis assembled from those numbers

Usage: python tools/render_failures.py [--top 6]
"""
import argparse
import collections
import json
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_CN = {
    0: "安全帽",
    1: "口罩",
    2: "未戴安全帽",
    3: "未戴口罩",
    4: "未穿反光背心",
    5: "人",
    6: "锥桶",
    7: "反光背心",
    8: "机械",
    9: "车辆",
}
GT_CLASSES = ["helmet", "no-helmet", "no-vest", "person", "vest"]
GT_CN = {
    "helmet": "安全帽",
    "no-helmet": "未戴安全帽",
    "no-vest": "未穿反光背心",
    "person": "人",
    "vest": "反光背心",
}
MAP_MODEL_TO_GT = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4}

COL_OK = (46, 204, 113)
COL_FP = (60, 60, 235)
COL_FN = (0, 150, 255)


def imread(path):
    return cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)


def imwrite(path, img):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise IOError(path)
    buf.tofile(path)


def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    aa = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    bb = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return inter / max(aa + bb - inter, 1e-9)


def load_gt(path, w, h):
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if len(p) < 5:
                continue
            c = int(float(p[0]))
            cx, cy, bw, bh = [float(v) for v in p[1:5]]
            out.append(
                (c, [(cx - bw / 2) * w, (cy - bh / 2) * h,
                     (cx + bw / 2) * w, (cy + bh / 2) * h])
            )
    return out


def chip(img, text, x, y, color):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    top = max(0, y - th - 8)
    cv2.rectangle(img, (x, top), (x + tw + 6, y), color, -1)
    cv2.putText(img, text, (x + 3, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                (255, 255, 255), 1, cv2.LINE_AA)


def dashed_rect(img, box, color, thick=2, dash=9):
    x1, y1, x2, y2 = [int(round(v)) for v in box]
    for (ax, ay, bx, by) in ((x1, y1, x2, y1), (x2, y1, x2, y2),
                             (x2, y2, x1, y2), (x1, y2, x1, y1)):
        length = max(abs(bx - ax), abs(by - ay))
        steps = max(1, length // dash)
        for k in range(0, steps, 2):
            t0, t1 = k / steps, min(1.0, (k + 1) / steps)
            p0 = (int(ax + (bx - ax) * t0), int(ay + (by - ay) * t0))
            p1 = (int(ax + (bx - ax) * t1), int(ay + (by - ay) * t1))
            cv2.line(img, p0, p1, color, thick, cv2.LINE_AA)
    return img


def size_bucket(box):
    side = float(np.sqrt(max(0.0, (box[2] - box[0]) * (box[3] - box[1]))))
    if side < 48:
        return "小"
    if side < 96:
        return "中"
    return "大"


def analyse(gt, dets, conf=0.35, thr=0.5):
    """Greedy match, returning TP/FP/FN structure."""
    dets = [d for d in dets if d["score"] >= conf]
    dets.sort(key=lambda d: -d["score"])
    used = set()
    hits = []      # (gt_index, det)
    fps = []       # det
    for d in dets:
        gc = MAP_MODEL_TO_GT.get(int(d["cls_id"]))
        best, bi = 0.0, -1
        if gc is None:
            # classes outside the 5 reported ones (mask / cone / machinery /
            # vehicle) are not annotated in this dataset, so a box on them is
            # neither a hit nor a false positive -- same rule as eval_vs_gt.
            continue
        if gc is not None:
            for j, (c, box) in enumerate(gt):
                if j in used or c != gc:
                    continue
                v = iou(d["xyxy"], box)
                if v > best:
                    best, bi = v, j
        if best >= thr:
            used.add(bi)
            hits.append((bi, d))
        else:
            fps.append(d)
    fns = [j for j in range(len(gt)) if j not in used]
    return hits, fps, fns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--pred", default=None)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "web", "assets3"))
    args = ap.parse_args()

    pred_path = args.pred or os.path.join(ROOT, "out", "ab_pred_A_test.json")
    with open(pred_path, encoding="utf-8") as f:
        preds = json.load(f)

    img_dir = os.path.join(ROOT, args.split, "images")
    lbl_dir = os.path.join(ROOT, args.split, "labels")

    rows = []
    for name, payload in preds.items():
        stem = os.path.splitext(name)[0]
        img = imread(os.path.join(img_dir, name))
        if img is None:
            continue
        h, w = img.shape[:2]
        gt = load_gt(os.path.join(lbl_dir, stem + ".txt"), w, h)
        if not gt:
            continue
        hits, fps, fns = analyse(gt, payload["detections"], args.conf)
        rows.append(
            {
                "file": name,
                "stem": stem,
                "size": [w, h],
                "n_gt": len(gt),
                "n_hit": len(hits),
                "n_fp": len(fps),
                "n_fn": len(fns),
                "gt": gt,
                "fps": [(d["cls_id"], d["xyxy"], d["score"]) for d in fps],
                "hits": [(j, d["cls_id"], d["xyxy"], d["score"]) for j, d in hits],
                "fns": [(gt[j][0], gt[j][1]) for j in fns],
            }
        )

    # rank: missed boxes weigh more than false positives (missing a violation
    # is costlier than an extra box for a demo assistant)
    rows.sort(key=lambda r: (-(r["n_fn"] * 2 + r["n_fp"]), -r["n_gt"]))
    picked = rows[: args.top]

    os.makedirs(args.out_dir, exist_ok=True)
    out_rows = []
    for r in picked:
        img = imread(os.path.join(img_dir, r["file"]))
        imwrite(os.path.join(args.out_dir, "orig_%s.jpg" % r["stem"]), img)

        vis = img.copy()
        for _, cid, box, score in r["hits"]:
            x1, y1, x2, y2 = [int(round(v)) for v in box]
            cv2.rectangle(vis, (x1, y1), (x2, y2), COL_OK, 2, cv2.LINE_AA)
            chip(vis, "%s %.2f" % (MODEL_CN[cid], score), x1, y1, COL_OK)
        for cid, box, score in r["fps"]:
            x1, y1, x2, y2 = [int(round(v)) for v in box]
            cv2.rectangle(vis, (x1, y1), (x2, y2), COL_FP, 2, cv2.LINE_AA)
            chip(vis, "误检 %s %.2f" % (MODEL_CN[cid], score), x1, y1, COL_FP)
        for c, box in r["fns"]:
            dashed_rect(vis, box, COL_FN)
            x1, y1 = int(round(box[0])), int(round(box[1]))
            chip(vis, "漏检 %s" % GT_CN[GT_CLASSES[c]], x1, y1, COL_FN)
        imwrite(os.path.join(args.out_dir, "pred_%s.jpg" % r["stem"]), vis)

        miss = collections.Counter(GT_CLASSES[c] for c, _ in r["fns"])
        miss_size = collections.Counter(size_bucket(b) for _, b in r["fns"])
        fp_c = collections.Counter(MODEL_CN[cid] for cid, _, _ in r["fps"])
        gt_c = collections.Counter(GT_CLASSES[c] for c, _ in r["gt"])

        note = []
        if r["fns"]:
            note.append(
                "漏检 %d 个：%s"
                % (len(r["fns"]),
                   "、".join("%s %d" % (GT_CN[k], v) for k, v in miss.most_common()))
            )
            if miss_size:
                note.append(
                    "漏掉的框以「%s」目标为主" % miss_size.most_common(1)[0][0]
                )
        if r["fps"]:
            note.append(
                "误检 %d 个：%s"
                % (len(r["fps"]),
                   "、".join("%s %d" % (k, v) for k, v in fp_c.most_common()))
            )
        out_rows.append(
            {
                "file": r["file"],
                "stem": r["stem"],
                "size": r["size"],
                "gt_total": len(r["gt"]),
                "gt": {GT_CN[k]: v for k, v in gt_c.items()},
                "tp": len(r["hits"]),
                "fp": len(r["fps"]),
                "fn": len(r["fns"]),
                "missed": {GT_CN[k]: v for k, v in miss.items()},
                "missed_size": dict(miss_size),
                "false_pos": dict(fp_c),
                "note": "；".join(note),
            }
        )
        print("%-52s gt=%2d tp=%2d fp=%2d fn=%2d  %s"
              % (r["file"][:52], len(r["gt"]), len(r["hits"]),
                 len(r["fps"]), len(r["fns"]), "；".join(note)))

    with open(os.path.join(ROOT, "out", "failure_stats.json"), "w",
              encoding="utf-8") as f:
        json.dump(out_rows, f, ensure_ascii=False, indent=1)
    print("written:", os.path.join(ROOT, "out", "failure_stats.json"))
    print("images:", len(out_rows), "->", args.out_dir)


if __name__ == "__main__":
    main()
