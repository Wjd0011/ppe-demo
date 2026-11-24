# -*- coding: utf-8 -*-
"""Self-test: load both X-AnyLabeling custom model configs with the *app's own*
YOLO class (not our onnxruntime wrapper) and run one image through them.

    python tools/test_xal_model.py                      # both yamls, demo2 第 1 张
    python tools/test_xal_model.py --image some.jpg
    python tools/test_xal_model.py --config models/ppe_demo_trained.yaml

This is the check that answers "does 自动标注 actually work after I clone this
repo?" -- it exercises the same code path the GUI uses (config file ->
get_model_abs_path -> preprocess / inference / postprocess), so a wrong
model_path or a GBK-decoding config file fails here instead of inside the app.

Requires the GUI stack (`x-anylabeling-cvhub[cpu]`). If it lives in another
interpreter, point XAL_SITE_PACKAGES at that site-packages directory.
"""
import argparse
import os
import sys

try:  # 中文类别名在 GBK 控制台会乱码，统一按 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001 - 老 Python / 重定向到文件时忽略
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_extra = os.environ.get("XAL_SITE_PACKAGES")
if _extra:
    sys.path.insert(0, _extra)

CONFIGS = [
    os.path.join(ROOT, "models", "ppe_yolov8n.yaml"),
    os.path.join(ROOT, "models", "ppe_demo_trained.yaml"),
]
DEFAULT_IMAGE = os.path.join(ROOT, "demo2", "images")


def pick_image(folder):
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
            return os.path.join(folder, name)
    return None


def run_one(cfg_path, image_path):
    import cv2
    import numpy as np
    import yaml

    import anylabeling.config as cfgmod
    from anylabeling.services.auto_labeling.yolov8 import YOLO

    # the app reads ~/.xanylabelingrc for global defaults; set it explicitly so
    # this script behaves the same when run from a bare checkout
    if not getattr(cfgmod, "current_config_file", None):
        cfgmod.current_config_file = os.path.join(
            os.path.expanduser("~"), ".xanylabelingrc"
        )

    cfg_path = os.path.abspath(cfg_path)
    with open(cfg_path, "r", encoding="utf-8") as f:
        model_config = yaml.safe_load(f)
    model_config["config_file"] = cfg_path

    model = YOLO(model_config, lambda msg: None)
    model.set_auto_labeling_conf(float(model_config.get("conf_threshold", 0.35)))
    model.set_auto_labeling_iou(float(model_config.get("iou_threshold", 0.45)))

    abs_path = model.get_model_abs_path(model_config, "model_path")
    if not os.path.exists(abs_path):
        raise FileNotFoundError("model_path 解析到不存在的文件: %s" % abs_path)

    # cv2.imread 读不了中文路径
    bgr = cv2.imdecode(np.fromfile(image_path, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise IOError("readable image expected: %s" % image_path)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    model.image_shape = rgb.shape
    blob = model.preprocess(rgb, upsample_mode="letterbox")
    outputs = model.inference(blob)
    boxes, class_ids, scores, _masks, _kps = model.postprocess(outputs)

    print("[ok] %s" % os.path.relpath(cfg_path, ROOT))
    print("     model_path -> %s" % os.path.relpath(abs_path, ROOT))
    print("     classes=%d  boxes=%d" % (len(model.classes), len(boxes)))
    for cls_id, score in list(zip(class_ids, scores))[:5]:
        print("     %-12s %.3f" % (model.classes[int(cls_id)], float(score)))
    return len(boxes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", action="append", default=None,
                    help="yaml to test (repeatable); default = both models/")
    ap.add_argument("--image", default=None,
                    help="image file; default = first image in demo2/images")
    args = ap.parse_args()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])  # noqa: F841

    image_path = args.image or pick_image(DEFAULT_IMAGE)
    if not image_path or not os.path.exists(image_path):
        print("no test image; pass --image")
        return 2
    print("image: %s\n" % os.path.relpath(image_path, ROOT))

    configs = args.config or CONFIGS
    failed = 0
    for cfg in configs:
        try:
            run_one(cfg, image_path)
        except BaseException as e:  # noqa: BLE001 - report, keep going
            failed += 1
            print("[FAIL] %s -> %s: %s" % (cfg, type(e).__name__, e))
        print()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
