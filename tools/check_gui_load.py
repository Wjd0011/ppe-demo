"""Headless check: run the app's real main() with the demo folder and snapshot
what the GUI loaded *after* the event loop has started (images and annotations
are loaded on show, not during construction).

app.main() does `from anylabeling.views.mainwindow import MainWindow` inside the
function, so the class must be replaced on the source module. QApplication.exec
is stubbed; it processes events for a moment, snapshots, then hard-exits (Qt
teardown on a headless platform is noisy).
"""
import json
import os
import sys
import time
import traceback

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_extra = os.environ.get("XAL_SITE_PACKAGES")
if _extra:                      # 可选：X-AnyLabeling 装在别的 venv 里时指过去
    sys.path.insert(0, _extra)

from PyQt6 import QtWidgets

import anylabeling.app as appmod
import anylabeling.views.mainwindow as mwmod

DEMO_DIR = os.environ.get("DEMO_DIR", os.path.join(ROOT, "demo2", "images"))
OUT = os.environ.get("GUI_CHECK_OUT", os.path.join(ROOT, "out", "gui_check.json"))
STATE = {}

RealMainWindow = mwmod.MainWindow


def snapshot(win):
    view = win.labeling_widget.view
    labels = []
    for it in view.label_list:
        sh = it.shape()          # LabelListWidgetItem.shape() returns the Shape
        if sh is not None:
            labels.append(sh.label)
    shapes = [s.label for s in view.canvas.shapes]
    files = list(getattr(view, "image_list", []) or [])
    data = dict(
        stage="snapshot",
        filename=view.filename,
        n_files=len(files),
        label_list=labels,
        shape_labels=shapes,
        title=win.windowTitle(),
        files_sample=files[:2],
    )
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


class RecordingWindow(RealMainWindow):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        STATE["win"] = self


def fake_exec(self):
    win = STATE.get("win")
    if win is None:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"stage": "no-window"}, f)
        os._exit(1)
    deadline = time.time() + 6.0
    while time.time() < deadline:
        self.processEvents()
        time.sleep(0.05)
        if getattr(win.labeling_widget.view, "canvas", None) is not None:
            if win.labeling_widget.view.canvas.shapes or time.time() > deadline - 4:
                pass
    try:
        data = snapshot(win)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except BaseException:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump({"stage": "snapshot-failed", "traceback": traceback.format_exc()}, f, ensure_ascii=False)
        sys.stdout.flush()
        os._exit(1)
    sys.stdout.flush()
    os._exit(0)


mwmod.MainWindow = RecordingWindow
QtWidgets.QApplication.exec = fake_exec

try:
    sys.argv = ["launch", "--filename", DEMO_DIR]
    appmod.main()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"stage": "main-returned"}, f)
    os._exit(1)
except SystemExit:
    pass
except BaseException:
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"stage": "main-crashed", "traceback": traceback.format_exc()}, f, ensure_ascii=False)
    os._exit(1)
os._exit(1)
