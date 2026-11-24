# -*- coding: utf-8 -*-
"""Build the classroom demo image set.

Steps
  1. scan every split, keep images that contain at least one Person
  2. rank by "interesting-ness" (has vest / helmet / no-vest / no-helmet)
  3. copy N images into demo/images, plus their GT labels
  4. write a manifest so the webpage can describe each picture
"""
import argparse
import collections
import json
import os
import shutil

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = ["helmet", "no-helmet", "no-vest", "person", "vest"]


def read_gt(path):
    counts = collections.Counter()
    boxes = []
    if not os.path.isfile(path):
        return counts, boxes
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if len(p) < 5:
                continue
            c = int(float(p[0]))
            counts[c] += 1
            boxes.append([c] + [float(v) for v in p[1:5]])
    return counts, boxes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-split", default="test:14,valid:10,train:8")
    ap.add_argument("--out", default=os.path.join(ROOT, "demo", "images"))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    label_out = os.path.join(os.path.dirname(args.out), "labels")
    os.makedirs(label_out, exist_ok=True)

    plan = {}
    for part in args.per_split.split(","):
        split, n = part.split(":")
        plan[split.strip()] = int(n)

    manifest = []
    for split, want in plan.items():
        img_dir = os.path.join(ROOT, split, "images")
        lbl_dir = os.path.join(ROOT, split, "labels")
        if not os.path.isdir(img_dir):
            continue
        scored = []
        for fn in sorted(os.listdir(img_dir)):
            if not fn.lower().endswith(".jpg"):
                continue
            stem = os.path.splitext(fn)[0]
            counts, boxes = read_gt(os.path.join(lbl_dir, stem + ".txt"))
            if counts[3] == 0:  # no person -> not useful for a PPE demo
                continue
            score = (
                counts[3] * 1.0
                + counts[4] * 1.5  # vest
                + counts[0] * 1.5  # helmet
                + counts[2] * 2.0  # no-vest (violation)
                + counts[1] * 4.0  # no-helmet (rare, very valuable)
            )
            scored.append((score, fn, counts, boxes))
        scored.sort(key=lambda t: -t[0])
        picked = scored[:want]
        # interleave so the demo is not all-violation images in a row
        for score, fn, counts, boxes in picked:
            src = os.path.join(img_dir, fn)
            dst_name = "%s__%s" % (split, fn)
            shutil.copyfile(src, os.path.join(args.out, dst_name))
            shutil.copyfile(
                os.path.join(lbl_dir, os.path.splitext(fn)[0] + ".txt"),
                os.path.join(label_out, os.path.splitext(dst_name)[0] + ".txt"),
            )
            manifest.append(
                {
                    "file": dst_name,
                    "split": split,
                    "source": fn,
                    "counts": {CLASSES[k]: v for k, v in sorted(counts.items())},
                    "score": round(score, 1),
                }
            )

    with open(
        os.path.join(os.path.dirname(args.out), "manifest.json"),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print("demo images:", len(manifest))
    for m in manifest:
        print("  ", m["file"][:40], m["counts"])


if __name__ == "__main__":
    main()
