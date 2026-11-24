# -*- coding: utf-8 -*-
"""Render the demo visuals for the webpage.

For every image in demo/images it produces:
    assets/orig_<stem>.jpg   original photo
    assets/gt_<stem>.jpg     ground-truth boxes (dataset labels)
    assets/pred_<stem>.jpg   model boxes (from the X-AnyLabeling JSON)
and a stats entry: TP / FP / FN at IoU 0.5 for the 5 PPE classes.

The drawing mirrors what X-AnyLabeling shows on the canvas: a rectangle plus a
filled label chip with the class name and confidence.
"""
import collections
import json
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_IMG = os.path.join(ROOT, "demo", "images")
DEMO_LBL = os.path.join(ROOT, "demo", "labels")
ASSETS = os.path.join(ROOT, "web", "assets")

# dataset class order
GT_CLASSES = ["helmet", "no-helmet", "no-vest", "person", "vest"]
GT_CN = {
    "helmet": "安全帽",
    "no-helmet": "未戴安全帽",
    "no-vest": "未穿反光背心",
    "person": "人",
    "vest": "反光背心",
}
GT_COLORS = {
    "helmet": (46, 204, 113),
    "no-helmet": (231, 76, 60),
    "no-vest": (230, 126, 34),
    "person": (52, 152, 219),
    "vest": (26, 188, 156),
}

# model class -> dataset class (None = shown grey, not scored)
# Keys are the Chinese labels written into the JSON annotations.
MODEL_MAP = {
    "安全帽": "helmet",
    "未戴安全帽": "no-helmet",
    "未穿反光背心": "no-vest",
    "人": "person",
    "反光背心": "vest",
}
OTHER_MODEL = {"口罩", "未戴口罩", "锥桶", "机械", "车辆"}


def imread(path):
    return cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)


def imwrite(path, img):
    ok, buf = cv2.imencode(os.path.splitext(path)[1] or ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise IOError(path)
    buf.tofile(path)


def bbox_from_points(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def iou(a, b):
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    # dataset boxes come from normalized cx/cy/w/h -> compute areas the same way
    aa = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    bb = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return inter / max(aa + bb - inter, 1e-9)


def load_gt(stem, w, h, label_dir=None):
    path = os.path.join(label_dir or DEMO_LBL, stem + ".txt")
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
                (
                    GT_CLASSES[c],
                    [(cx - bw / 2) * w, (cy - bh / 2) * h,
                     (cx + bw / 2) * w, (cy + bh / 2) * h],
                )
            )
    return out


def load_pred(stem, image_dir=None):
    path = os.path.join(image_dir or DEMO_IMG, stem + ".json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for s in data.get("shapes", []):
        out.append(
            (
                s["label"],
                bbox_from_points(s["points"]),
                float(s.get("score", 0.0)),
                MODEL_MAP.get(s["label"]),
            )
        )
    return out


def draw_boxes(img, items, show_score=True, alpha=0.55):
    """items: list of (label, box, color, text)."""
    vis = img.copy()
    for label, box, color, text in items:
        x1, y1, x2, y2 = [int(round(v)) for v in box]
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        top = max(0, y1 - th - 8)
        cv2.rectangle(vis, (x1, top), (x1 + tw + 6, y1), color, -1)
        cv2.putText(vis, text, (x1 + 3, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                    0.45, (255, 255, 255), 1, cv2.LINE_AA)
    return vis


def match(preds, gts, thr=0.5):
    """Greedy match on the 5 scored classes -> TP/FP/FN."""
    p = [(d[3], d[1]) for d in preds if d[3] is not None]
    g = list(gts)
    used = set()
    tp = []
    fp = []
    for c, b in p:
        best, bi = 0.0, -1
        for i, (gc, gb) in enumerate(g):
            if i in used or gc != c:
                continue
            v = iou(b, gb)
            if v > best:
                best, bi = v, i
        if best >= thr:
            used.add(bi)
            tp.append((c, b))
        else:
            fp.append((c, b))
    fn = [g[i] for i in range(len(g)) if i not in used]
    return tp, fp, fn


def main():
    os.makedirs(ASSETS, exist_ok=True)
    files = sorted(
        f for f in os.listdir(DEMO_IMG) if f.lower().endswith(".jpg")
    )
    stats = []
    for fn in files:
        stem = os.path.splitext(fn)[0]
        img = imread(os.path.join(DEMO_IMG, fn))
        if img is None:
            continue
        h, w = img.shape[:2]
        gts = load_gt(stem, w, h)
        preds = load_pred(stem)
        tp, fp, fns = match(preds, gts)

        imwrite(os.path.join(ASSETS, "orig_%s.jpg" % stem), img)

        gt_items = [
            (c, b, GT_COLORS[c], "%s" % GT_CN[c]) for c, b in gts
        ]
        imwrite(os.path.join(ASSETS, "gt_%s.jpg" % stem), draw_boxes(img, gt_items))

        pred_items = []
        for label, box, score, mapped in preds:
            if mapped is None:
                continue
            color = GT_COLORS[mapped]
            text = "%s %.2f" % (GT_CN[mapped], score)
            pred_items.append((label, box, color, text))
        imwrite(os.path.join(ASSETS, "pred_%s.jpg" % stem), draw_boxes(img, pred_items))

        cnt = collections.Counter(c for c, _ in gts)
        stats.append(
            {
                "file": fn,
                "stem": stem,
                "size": [w, h],
                "gt": {GT_CN[k]: v for k, v in cnt.items()},
                "gt_total": len(gts),
                "pred_total": len(pred_items),
                "tp": len(tp),
                "fp": len(fp),
                "fn": len(fns),
                "fn_classes": dict(collections.Counter(c for c, _ in fns)),
                "fp_classes": dict(collections.Counter(c for c, _ in fp)),
            }
        )

    with open(os.path.join(ROOT, "out", "demo_stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)
    print("rendered:", len(stats), "images ->", ASSETS)
    tp = sum(s["tp"] for s in stats)
    fp = sum(s["fp"] for s in stats)
    fn = sum(s["fn"] for s in stats)
    print("TP %d  FP %d  FN %d  |  P %.3f  R %.3f" % (
        tp, fp, fn, tp / max(1, tp + fp), tp / max(1, tp + fn)))


if __name__ == "__main__":
    main()
