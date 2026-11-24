# -*- coding: utf-8 -*-
"""Verify the demo annotations load through X-AnyLabeling's own LabelFile
loader (the code path the GUI uses when it opens a .json next to the image),
and sanity-check the rendered screenshot is not blank."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_extra = os.environ.get("XAL_SITE_PACKAGES")
if _extra:                      # 可选：X-AnyLabeling 装在别的 venv 里时指过去
    sys.path.insert(0, _extra)

import numpy as np
from PIL import Image
from PyQt6.QtCore import QCoreApplication

from anylabeling.views.labeling.label_file import LabelFile

app = QCoreApplication(sys.argv)

demo = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "demo", "images")
files = sorted(f for f in os.listdir(demo) if f.endswith(".json"))
print("dir:", demo)
print("json files:", len(files))

total = 0
lf = LabelFile()
for fn in files[:5]:
    path = os.path.join(demo, fn)
    lf.load(path)
    labels = [s.label for s in lf.shapes]
    total += len(labels)
    print("%-46s %2d shapes | %s" % (
        fn[:46], len(labels), ", ".join(sorted(set(labels)))))
print("loaded shapes in first 5:", total)

shot = os.path.join(ROOT, "out", "shot", "page.png")
if os.path.isfile(shot):
    im = Image.open(shot).convert("RGB")
    a = np.asarray(im)
    print("screenshot:", im.size, "| mean", a.mean().round(1),
          "| std", a.std().round(1), "| unique rows",
          len(np.unique(a.reshape(-1, 3), axis=0)))
    # header should be dark, and there must be bright text pixels somewhere
    print("bright px ratio: %.4f" % float((a.mean(2) > 200).mean()))
