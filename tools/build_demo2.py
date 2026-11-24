# -*- coding: utf-8 -*-
"""Pick construction-site photos for the expanded demo/test set.

Selection rules (all data is from a construction-site dataset already):
  * must contain at least one `person` box -> there is a work scene with people
  * prefer images that show the three PPE situations we must demo:
        compliant (helmet + vest), missing vest, missing helmet
  * keep a spread across splits so the set is not all one camera/scene

Writes:
    demo2/images/*.jpg          selected photos
    demo2/labels/*.txt          GT labels (YOLO)
    demo2/manifest.json         per-image class counts + why it was picked
    out/demo2_source.json       provenance of every file
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "demo2")
CLASSES = ["helmet", "no-helmet", "no-vest", "person", "vest"]


def read_counts(path):
    c = [0] * 5
    if not os.path.isfile(path):
        return c
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if len(p) >= 5:
                i = int(float(p[0]))
                if 0 <= i < 5:
                    c[i] += 1
    return c


def main():
    img_out = os.path.join(OUT, "images")
    lbl_out = os.path.join(OUT, "labels")
    os.makedirs(img_out, exist_ok=True)
    os.makedirs(lbl_out, exist_ok=True)

    pools = {"compliant": [], "no_vest": [], "no_helmet": [], "mixed": []}
    for split in ("test", "valid", "train"):
        img_dir = os.path.join(ROOT, split, "images")
        lbl_dir = os.path.join(ROOT, split, "labels")
        if not os.path.isdir(img_dir):
            continue
        for fn in sorted(os.listdir(img_dir)):
            if not fn.lower().endswith(".jpg"):
                continue
            stem = os.path.splitext(fn)[0]
            lbl = os.path.join(lbl_dir, stem + ".txt")
            if not os.path.isfile(lbl):
                continue
            helmet, no_helmet, no_vest, person, vest = read_counts(lbl)
            if person == 0:
                continue  # no work scene / no people -> not useful for PPE demo
            entry = {
                "split": split,
                "file": fn,
                "stem": stem,
                "counts": dict(zip(CLASSES, [helmet, no_helmet, no_vest, person, vest])),
            }
            if no_helmet and no_vest:
                pools["mixed"].append(entry)
            elif no_helmet:
                pools["no_helmet"].append(entry)
            elif no_vest:
                pools["no_vest"].append(entry)
            else:
                pools["compliant"].append(entry)

    # quotas: enough variety, but every bucket represented
    quota = {"mixed": 14, "no_helmet": 14, "no_vest": 18, "compliant": 14}
    picked = []
    for key, n in quota.items():
        items = pools[key]
        # de-duplicate by stem prefix (roboflow copies images between splits)
        seen = set()
        uniq = []
        for e in items:
            if e["stem"] in seen:
                continue
            seen.add(e["stem"])
            uniq.append(e)
        # spread: take every k-th so we do not grab 12 frames of one scene
        if len(uniq) > n:
            step = len(uniq) / float(n)
            sel = [uniq[min(len(uniq) - 1, int(i * step))] for i in range(n)]
        else:
            sel = uniq
        picked.extend(sel)
        print("%-10s pool %4d -> picked %2d" % (key, len(uniq), len(sel)))

    manifest = []
    for e in picked:
        src_img = os.path.join(ROOT, e["split"], "images", e["file"])
        src_lbl = os.path.join(ROOT, e["split"], "labels", e["stem"] + ".txt")
        dst_name = "%s__%s" % (e["split"], e["file"])
        shutil.copyfile(src_img, os.path.join(img_out, dst_name))
        shutil.copyfile(src_lbl, os.path.join(lbl_out, os.path.splitext(dst_name)[0] + ".txt"))
        manifest.append(
            {
                "file": dst_name,
                "split": e["split"],
                "source_file": e["file"],
                "counts": e["counts"],
            }
        )

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print("selected:", len(manifest))
    tot = {k: 0 for k in CLASSES}
    for m in manifest:
        for k, v in m["counts"].items():
            tot[k] += v
    print("box totals:", tot)


if __name__ == "__main__":
    main()
