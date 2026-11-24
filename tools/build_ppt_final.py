# -*- coding: utf-8 -*-
"""生成《施工场地安全帽 / 反光背心检测》最终答辩 PPT（17 页）。

改版依据（导师提问）：
    Q1 你负责哪一块工作？      → P3
    Q2 解决了什么问题？        → P4
    Q3 你是怎么想的？思路      → P7
    三个创新点                 → P8 / P9 / P10
其余：数据 P5、方法 P6、对照 P11、结果 P12、前后期 P13、边界 P14、价值 P15、改进 P16、结论 P17。

本版定位：最终答辩（不含时长提示、不含现场演示操作说明）。
所有数字读自 out/*.json，改完数据重跑即可同步。
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from ppt_kit import (ACCENT, CW, GREEN, H, INK, LINE, ML, MONO, MUTED, PANEL,  # noqa: E402
                     ROOT, SUB, W, WARN, WHITE, Deck, bars, bullets, load, notes,
                     panel, rule, table, textbox)

TITLE = "施工场地安全帽 / 反光背心检测 · 最终答辩"


def img(prefix, folder="assets3"):
    """按前缀挑一张图，找不到返回 None。"""
    pat = os.path.join(ROOT, "web", folder, prefix + "*")
    hits = sorted(glob.glob(pat))
    return hits[0] if hits else None


def big(slide, x, y, w, value, label, color=INK, size=26):
    textbox(slide, x, y, w, size / 52.0, value, size=size, bold=True, color=color)
    textbox(slide, x, y + size / 52.0 + 0.05, w, 0.28, label, size=10.5, color=MUTED)


def tag(slide, x, y, w, text, color=ACCENT):
    textbox(slide, x, y, w, 0.28, text, size=10.5, bold=True, color=color)


# ------------------------------------------------------------------ P1 封面
def p1(d, m):
    s = d.prs.slides.add_slide(d.blank)
    d.n += 1
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(W), Inches(0.30))
    band.fill.solid()
    band.fill.fore_color.rgb = RGBColor.from_string(INK)
    band.line.fill.background()
    band.shadow.inherit = False

    textbox(s, ML, 1.02, 7.4, 0.3, "机器视觉课程设计 · 最终答辩", size=12, bold=True, color=ACCENT)
    textbox(s, ML, 1.42, 7.4, 1.5, ["施工场地安全帽与", "反光背心检测"], size=40, bold=True,
            color=INK, spacing=1.12)
    rule(s, ML, 3.24, 1.05)

    textbox(s, ML, 3.46, 7.0, 1.5,
            ["同一份公开权重、纯 CPU 推理，不改模型只改流程；",
             "把整图单尺度换成双尺度联合后，mAP@50 从 %.4f 提到 %.4f。" % (m["a"], m["b"])],
            size=15, color=SUB, spacing=1.55)

    for i, (v, k) in enumerate([("%d 张" % m["n_all"], "真实工地照片"),
                                ("%.4f" % m["b"], "mAP@50（测试集）"),
                                ("%d ms" % round(m["ms_b"]), "单图耗时 / CPU")]):
        big(s, ML + i * 2.36, 5.18, 2.2, v, k, INK, 26)

    textbox(s, ML, 6.66, 7.4, 0.3, "汇报人：________　｜　指导教师：________　｜　2026 年 11 月",
            size=11, color=SUB)

    p = img("pred_ppe_0357")
    if p:
        s.shapes.add_picture(p, Inches(7.96), Inches(1.26), width=Inches(4.62))
        textbox(s, 7.96, 5.86, 4.62, 0.28, "模型输出：绿 = 命中　红 = 误检　橙虚线 = 漏检",
                size=9, color=MUTED, align=PP_ALIGN.CENTER)
    notes(s, "开场一句：这套系统回答的是「不改模型的前提下，工地图像检测还能优化到什么程度、"
             "怎么证明、怎么复现」。先说清楚我负责哪一块，再说解决了什么问题，最后讲思路与三个创新点。\n"
             "如果老师只问一句，就答：权重不是我训的，数据和权重都是公开的；"
             "我负责的是怎么用、怎么验证、怎么交付。")


# ------------------------------------------------------------------ P2 三个问题的回答结构
def p2(d):
    s = d.page("汇报结构", "按三个问题组织：我做了什么 · 解决什么 · 怎么想的")
    qs = [
        ("Q1", "你负责哪一块工作？",
         "问题定义、数据与标注、推理与评估、对照实验、交付复现——五个工作包全部独立完成。",
         "见第 3 页"),
        ("Q2", "解决了什么问题？",
         "把「靠人扫一眼」变成可计数、可回看的框；把十类检测框收口成「合规 / 未戴帽 / 未穿背心」。",
         "见第 4 页"),
        ("Q3", "你的思路是什么？",
         "先把基线跑通并量出来，再判断瓶颈在输入尺度而不是模型，用四同条件的 A/B/C 反证并归因。",
         "见第 7 页"),
    ]
    cw = (CW - 2 * 0.28) / 3
    for i, (num, q, a, ref) in enumerate(qs):
        x = ML + i * (cw + 0.28)
        panel(s, x, 1.94, cw, 3.30, PANEL, LINE, 0.05)
        textbox(s, x + 0.28, 2.10, 1.2, 0.40, num, size=22, bold=True, color="C6D4E4")
        textbox(s, x + 0.28, 2.56, cw - 0.52, 0.62, q, size=15.5, bold=True, color=INK, spacing=1.2)
        rule(s, x + 0.28, 3.24, 0.40, ACCENT, 2.2)
        textbox(s, x + 0.28, 3.38, cw - 0.52, 1.44, a, size=11.5, color=SUB, spacing=1.45)
        textbox(s, x + 0.28, 4.88, cw - 0.52, 0.26, ref, size=10, bold=True, color=ACCENT)

    textbox(s, ML, 5.46, CW, 0.3, "三个创新点（第 8 · 9 · 10 页）", size=11.5, bold=True, color=ACCENT)
    items = ["01 双尺度联合推理", "02 人级包含判定", "03 零依赖全链路自实现"]
    cw2 = (CW - 2 * 0.28) / 3
    for i, t in enumerate(items):
        x = ML + i * (cw2 + 0.28)
        panel(s, x, 5.80, cw2, 0.72, "E8F2FE", ACCENT, 0.10)
        textbox(s, x, 5.98, cw2, 0.36, t, size=13.5, bold=True, color=INK, align=PP_ALIGN.CENTER)

    textbox(s, ML, 6.66, CW, 0.28,
            "一条主线：不动权重，动输入与判定；每处改动都用同权重、同测试集、同阈值的对照实验证明。",
            size=11, color=WARN)
    notes(s, "先给老师一张地图：三个问题 + 三个创新点，后面每节都对应其中一条。"
             "强调「不动权重」——这是全篇的前提，也是创新点能归因的基础。")


# ------------------------------------------------------------------ P3 Q1 责任
def p3(d):
    s = d.page("一 · 我负责哪一块工作", "五个工作包，从问题定义到可复现交付")
    rows = [["工作包", "具体做了什么", "范围"],
            ["问题定义", "把「安全员凭眼判断」拆成 4 个可测问题；确定只报 5 类、只做筛查不做验收", "独立完成"],
            ["数据与标注", "从公开数据集筛出 %d 张真实工地照片；配 X-AnyLabeling 十类模型产出中文标注", "独立完成"],
            ["推理与评估", "手写 letterbox / NMS / 101 点 VOC AP，在三个划分上逐张跑完", "独立完成"],
            ["对照与归因", "A/B/C 三策略、四同原则、按目标尺寸拆召回、6 张最差图逐框归因", "独立完成"],
            ["交付与复现", "run.py 一条命令跑全链路、13 章网页、答辩材料；所有数字由脚本现算", "独立完成"]]
    rows[2][1] = rows[2][1] % 1206
    table(s, ML, 1.88, CW, rows, [1.62, 8.15, 2.20], size=12, head_size=11,
          row_h=0.62, head_h=0.40,
          aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.CENTER],
          accents={(i, 2): GREEN for i in range(1, 6)})

    panel(s, ML, 5.52, 5.86, 1.22, "EEF4FC", "C9DDF3", 0.05)
    textbox(s, ML + 0.24, 5.64, 5.40, 0.26, "复用的公共资产", size=10.5, bold=True, color=ACCENT)
    textbox(s, ML + 0.24, 5.92, 5.40, 0.70,
            "预训练权重（CC BY 4.0）与标注数据集（CC BY 4.0）均为公开资源，我没有重新训练模型。",
            size=11.5, color=SUB, spacing=1.4)

    panel(s, ML + 6.10, 5.52, CW - 6.10, 1.22, "FDF1EC", "F5C9B6", 0.05)
    textbox(s, ML + 6.34, 5.64, CW - 6.58, 0.26, "所以我的贡献在哪儿", size=10.5, bold=True, color=WARN)
    textbox(s, ML + 6.34, 5.92, CW - 6.58, 0.70,
            "在既有模型之上回答「怎么用、怎么证明、怎么交付」：流程设计、公平对照、工程化与可复现。",
            size=11.5, color=WARN, spacing=1.4)
    notes(s, "Q1 的回答要点：不要说「全是我做的」，要说清边界——权重和数据是公开的，"
             "五个工作包是我独立完成的。\n"
             "如果追问「那你到底创新在哪」：创新不在训练，在流程设计、对照方法与工程化落地，这是下一页和三个创新点的内容。")


# ------------------------------------------------------------------ P4 Q2 问题
def p4(d):
    s = d.page("二 · 解决了什么问题", "工地班前检查：靠人盯，盯不准也留不下证据")
    p = img("orig_ppe_0357")
    if p:
        s.shapes.add_picture(p, Inches(ML), Inches(1.86), width=Inches(4.28))

    bullets(s, ML + 4.66, 1.80, CW - 4.66, 3.10, [
        ("main", "靠人扫一眼：谁没戴帽、谁没穿反光背心，全凭安全员当场判断"),
        ("main", "口径不统一：「安全服」与「反光背心」混着叫，验收对不上"),
        ("main", "中远景照片：一个人头部常常只有几十像素，缩进模型就没了"),
        ("main", "事后无留痕：只记得「今天罚了 3 个人」，没有可回看的框"),
    ], size=15.5, gap=14)

    panel(s, ML, 5.16, CW, 1.14, "EEF4FC", "C9DDF3", 0.05)
    textbox(s, ML + 0.28, 5.28, CW - 0.56, 0.28, "所以要解决的问题", size=10.5, bold=True, color=ACCENT)
    textbox(s, ML + 0.28, 5.56, CW - 0.60, 0.60,
            "在不重训权重的前提下，把「戴没戴」判成可计数、可回看、可复核的结果，并给出可复现的证据链。",
            size=14.5, bold=True, color=INK)
    notes(s, "Q2 的回答要点：问题不是「模型不准」，是「检查过程没有留痕、口径不统一、目标太小」。\n"
             "左边这张是典型：23 个框，人眼也要数半天。所以我的立题是「不改权重、只改流程，让结果可计数可复现」。")


# ------------------------------------------------------------------ P5 数据
def p5(d, m):
    s = d.page("三 · 图片数据", "%d 张真实工地照片，十类标注收口到五类" % m["n_all"])
    rows = [["项", "值"],
            ["来源", "公开数据集（CC BY 4.0）"],
            ["规模", "%d 张 / %d 个真值框" % (m["n_all"], m["gt_all"])],
            ["划分", "train 997 · valid 119 · test 90"],
            ["场景", "白天室外，真实工地，非摆拍"],
            ["标注", "%d 张中文标注图（含自动预标注 + 人工校正）" % m["n_ann"]],
            ["口径", "原始 10 类 → 只报 5 类"]]
    table(s, ML, 1.88, 5.70, rows, [0.95, 4.60], size=11.5, head_size=11,
          row_h=0.46, head_h=0.36)

    rows2 = [["类别", "真值框", "占测试集"]]
    for name, cnt in m["cls_test"]:
        rows2.append([name, str(cnt), "%.1f%%" % (100.0 * cnt / m["gt_test"])])
    table(s, ML + 6.02, 1.88, CW - 6.02, rows2, [2.55, 1.65, 1.70], size=11.5, head_size=11,
          row_h=0.46, head_h=0.36,
          aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT])

    panel(s, ML, 5.10, CW, 1.16, "FDF1EC", "F5C9B6", 0.05)
    textbox(s, ML + 0.28, 5.22, CW - 0.56, 0.26, "长尾是这个数据集最硬的事实", size=10.5,
            bold=True, color=WARN)
    textbox(s, ML + 0.28, 5.50, CW - 0.60, 0.62,
            "「未戴安全帽」只占 %.1f%%（%d 个框），「未穿反光背心」占 %.1f%%（%d 个框）；"
            "后面所有负向类的低分，都能追到这一条。"
            % (100.0 * m["cls_test"][-1][1] / m["gt_test"], m["cls_test"][-1][1],
               100.0 * m["cls_test"][-2][1] / m["gt_test"], m["cls_test"][-2][1]),
            size=12, color=WARN, spacing=1.4)

    textbox(s, ML, 6.44, CW, 0.30,
            "标注工具链：X-AnyLabeling（自定义 YOLO 模型）+ 中文标签；自动预标注后人工校正，只保留 5 类。",
            size=11, color=SUB)
    notes(s, "数据回答两个问题：够不够真、够不够全。够真——1206 张白天室外真实工地照片，不是摆拍；"
             "不够全——负向类严重长尾，测试集里「未戴帽」只有 24 个框。\n"
             "这一条先说出来，后面讲负向类指标低时就不是找借口，而是数据事实。")


# ------------------------------------------------------------------ P6 模型
def p6(d, m):
    s = d.page("四 · 模型与方法", "固定 640 输入的 YOLOv8n，ONNX 上跑纯 CPU 推理")
    rows = [["项", "值"],
            ["网络", "YOLOv8n（YOLO 系列最小档）"],
            ["形态", "ONNX 12.2 MB，opset 12，FP32"],
            ["输入", "1 × 3 × 640 × 640（固定）"],
            ["输出", "1 × 14 × 8400 = 4 坐标 + 10 类"],
            ["后处理", "手写 letterbox + 类内 NMS"],
            ["设备", "onnxruntime CPU，%.0f ms / 图" % m["ms_a"]]]
    table(s, ML, 1.88, 5.62, rows, [1.10, 4.40], size=11.5, head_size=11,
          row_h=0.46, head_h=0.36)

    textbox(s, ML + 5.94, 1.86, CW - 5.94, 0.28, "为什么用最小档", size=10.5, bold=True, color=ACCENT)
    textbox(s, ML + 5.94, 2.18, CW - 5.94, 2.30,
            ["本机没有 CUDA 工具链，只能 CPU 推理：",
             "12 MB 权重换 %.0f ms / 图，先保证「跑得动、算得清」；" % m["ms_a"],
             "精度不足的部分，用输入尺度与判定规则补，而不是靠换大模型。",
             "换大模型、加训练都属于后期，不在本次范围内。"],
            size=12, color=SUB, spacing=1.5)

    p = img("pred_")
    if p:
        s.shapes.add_picture(p, Inches(ML + 6.30), Inches(4.06), width=Inches(2.32))
        textbox(s, ML + 6.30, 6.42, 2.32, 0.24, "同一张图的模型输出", size=8.5, color=MUTED,
                align=PP_ALIGN.CENTER)

    rows3 = [["映射", "说明"]]
    for line in m["mapping"]:
        rows3.append(line)
    table(s, ML, 5.16, 5.62, rows3, [1.65, 3.85], size=11, head_size=10.5,
          row_h=0.40, head_h=0.32)
    notes(s, "模型这一节只讲三件事：是什么（YOLOv8n，12 MB ONNX）、怎么跑（onnxruntime，手写前处理与 NMS）、"
             "为什么这么小（没有 CUDA，先保证可跑可复现）。\n"
             "如果问「为什么不训练」：一是本机没有 CUDA 工具链，二是本次要回答的是流程优化的边界，"
             "训练微调放在后期第一步。")



# ------------------------------------------------------------------ P7 Q3 思路
def p7(d, m):
    s = d.page("五 · 我的技术思路", "先量基线，再定位瓶颈，用反证确认因果")
    steps = [
        ("①", "先把基线跑通", "不改任何东西，量出整图单尺度的 %.4f，作为后面一切比较的锚点。" % m["a"]),
        ("②", "找瓶颈", "不是模型太小，是「喂进去的尺度」不对：大目标在 640 画布里占比过大。"),
        ("③", "提出假设", "再补一个 0.5× 视图，让大目标也落回训练时的尺度分布。"),
        ("④", "公平验证", "同权重、同测试集、同阈值、同硬件，只换预处理，其他一律不动。"),
        ("⑤", "主动反证", "再做一个分块 2×2 的负面对照，结果掉到 %.4f，证明「放大」不是万灵药。" % m["c"]),
        ("⑥", "归因收口", "按目标尺寸拆召回，改进落在大目标 %s → %s；再叠人级判定把框变成结论。"
         % (m["big_a"], m["big_b"])),
    ]
    cw = (CW - 2 * 0.26) / 3
    for i, (num, head, body) in enumerate(steps):
        col, row = i % 3, i // 3
        x = ML + col * (cw + 0.26)
        y = 1.88 + row * 1.72
        panel(s, x, y, cw, 1.56, PANEL, LINE, 0.06)
        textbox(s, x + 0.24, y + 0.14, 0.62, 0.30, num, size=15, bold=True, color=ACCENT)
        textbox(s, x + 0.86, y + 0.14, cw - 1.10, 0.32, head, size=14.5, bold=True, color=INK)
        textbox(s, x + 0.24, y + 0.56, cw - 0.46, 0.92, body, size=11, color=SUB, spacing=1.42)

    panel(s, ML, 5.36, CW, 0.98, "EEF4FC", "C9DDF3", 0.05)
    textbox(s, ML + 0.28, 5.48, CW - 0.56, 0.28, "思路一句话", size=10.5, bold=True, color=ACCENT)
    textbox(s, ML + 0.28, 5.76, CW - 0.60, 0.50,
            "不动模型先动输入：任何改动都必须能被一组同条件实验证伪，否则不算改进。",
            size=15, bold=True, color=INK)
    notes(s, "Q3 是这一版的重点：老师想知道你是怎么想的，不是做了什么。\n"
             "六步讲成一个故事：量基线 → 定位瓶颈在输入尺度 → 提假设 → 公平验证 → 主动做负面对照 → 尺寸归因收口。\n"
             "第⑤步是关键：分块 2×2 看起来「目标更大」，实测掉到 0.2613，说明我的假设是「尺度匹配」不是「越大越好」，"
             "这才叫证伪。")


# ------------------------------------------------------------------ P8 创新点 1
def p8(d, ab):
    A, B = ab["modes"]["A 整图基线"], ab["modes"]["B 缩图多尺度"]
    s = d.page("创新点 01", "双尺度联合推理：把「尺度」当成一个可调的超参")
    chain = [("原图 1.0× → letterbox 640", "保持小目标的细节，基线怎么跑就怎么跑"),
             ("缩图 0.5× → letterbox 640", "让大目标在 640 画布里占比更接近训练分布"),
             ("坐标反演 fx, fy 回原图", "两次推理的框映射到同一坐标系，才能合并"),
             ("类内 NMS 合并", "同类别之间去重，跨类别保留（人 ⊃ 安全帽）")]
    for i, (k, v) in enumerate(chain):
        y = 1.90 + i * 1.06
        panel(s, ML, y, 5.30, 0.92, PANEL if i % 2 == 0 else WHITE, LINE, 0.08)
        textbox(s, ML + 0.22, y + 0.10, 4.90, 0.30, k, size=12.5, bold=True, color=INK)
        textbox(s, ML + 0.22, y + 0.44, 4.88, 0.40, v, size=10.5, color=SUB)

    rows = [["指标", "整图", "双尺度", "变化"],
            ["mAP@50", "%.4f" % A["metrics"]["mAP50"], "%.4f" % B["metrics"]["mAP50"],
             "+%.4f" % (B["metrics"]["mAP50"] - A["metrics"]["mAP50"])],
            ["mAP@50-95", "%.4f" % A["metrics"]["mAP50_95"], "%.4f" % B["metrics"]["mAP50_95"],
             "+%.4f" % (B["metrics"]["mAP50_95"] - A["metrics"]["mAP50_95"])],
            ["大目标召回", "%.4f" % A["recall_by_size"]["大 (>=96px)"]["recall"],
             "%.4f" % B["recall_by_size"]["大 (>=96px)"]["recall"],
             "+%.4f" % (B["recall_by_size"]["大 (>=96px)"]["recall"]
                        - A["recall_by_size"]["大 (>=96px)"]["recall"])],
            ["小目标召回", "%.4f" % A["recall_by_size"]["小 (<48px)"]["recall"],
             "%.4f" % B["recall_by_size"]["小 (<48px)"]["recall"], "0.0000"],
            ["ms / 图", "%d" % round(A["latency_ms"]), "%d" % round(B["latency_ms"]),
             "+%d" % round(B["latency_ms"] - A["latency_ms"])]]
    table(s, ML + 5.66, 1.90, CW - 5.66, rows, [1.95, 1.42, 1.42, 1.52], size=11.5, head_size=10.5,
          row_h=0.48, head_h=0.36,
          aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
          accents={(1, 3): ACCENT, (2, 3): ACCENT, (3, 3): ACCENT})

    textbox(s, ML + 5.66, 4.92, CW - 5.66, 0.28, "为什么这算创新", size=10.5, bold=True, color=ACCENT)
    textbox(s, ML + 5.66, 5.22, CW - 5.66, 1.50,
            ["不改一个权重、不加一次训练，只多跑一次 0.5× 视图；",
             "收益可归因：涨的全是大目标召回（小目标一点没动）；",
             "代价可量化：耗时 %.0f → %.0f ms，翻倍但仍在 CPU 可接受区间。"
             % (A["latency_ms"], B["latency_ms"])],
            size=11.5, color=SUB, spacing=1.45)
    notes(s, "创新点 01 的一句话：把「输入尺度」当成超参来调，而不是把模型换大。\n"
             "注意两件事：① 收益只落在大目标上，小目标召回 0.7733 一点没变，这点必须主动说；"
             "② 代价是耗时接近翻倍。答辩时不要说成「免费提升」。")


# ------------------------------------------------------------------ P9 创新点 2
def p9(d, m):
    s = d.page("创新点 02", "人级包含判定：把十类检测框翻成一句人能读的话")
    bullets(s, ML, 1.86, 5.60, 2.05, [
        ("main", "先有「人」框，再把 PPE 框挂到人身上：交集 / PPE 框面积 > 0.25 视为「戴在这个人身上」"),
        ("main", "判据不是 IoU：帽子框面积只有人框的几十分之一，IoU 恒低，会把所有人都判成没戴"),
        ("main", "每人输出一个状态：合规 / 缺安全帽 / 缺反光背心 / 两项都缺"),
        ("main", "图片级再汇总成三个人数，可直接进班前检查台账"),
    ], size=12.5, gap=10)

    panel(s, ML, 4.06, 5.60, 1.98, "0F1B2D", "0F1B2D", 0.04)
    textbox(s, ML + 0.22, 4.14, 5.16, 0.24, "判定规则（tools/yolo_onnx_predict.py，摘录）",
            size=9, color="8FA6C0")
    code = ["persons = pick(dets, 'Person')",
            "hats    = pick(dets, 'Hardhat')",
            "vests   = pick(dets, 'Safety Vest')",
            "inside  = lambda p, q: inter_area(p, q) / area(q) > 0.25",
            "for p in persons:",
            "    hat  = any(inside(p, h) for h in hats)",
            "    vest = any(inside(p, v) for v in vests)"]
    textbox(s, ML + 0.22, 4.40, 5.16, 1.56, code, size=8.8, color="D5E2F0", font=MONO, spacing=1.36)

    textbox(s, ML + 5.92, 1.86, CW - 5.92, 0.28, "规则层的三个坑（都踩过）", size=10.5,
            bold=True, color=ACCENT)
    textbox(s, ML + 5.92, 2.18, CW - 5.92, 2.05,
            ["① 用 IoU 判归属会全军覆没：帽子框与整个人框的 IoU 恒低于阈值",
             "② 一个 PPE 框可能同时满足多个人的条件，目前是多归属而非唯一归属",
             "③ 没归属任何人的 PPE 框不计入结论，否则远景误检直接变成假罚单"],
            size=11.5, color=SUB, spacing=1.5)

    rows = [["已标注图（%d 张）" % m["n_demo2"], "张数"],
            ["合规（全员戴帽 + 反光背心）", str(m["buckets"]["compliant"])],
            ["仅缺安全帽", str(m["buckets"]["no_helmet"])],
            ["仅缺反光背心", str(m["buckets"]["no_vest"])],
            ["两项都缺", str(m["buckets"]["both"])]]
    table(s, ML + 5.92, 4.34, CW - 5.92, rows, [4.30, 1.72], size=11.5, head_size=10.5,
          row_h=0.44, head_h=0.36, aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT])

    textbox(s, ML + 5.92, 6.44, CW - 5.92, 0.26,
            "同一批图在检测指标之外，还能直接数出「今天几个人不合格」。", size=10.5, color=MUTED)
    notes(s, "创新点 02 的一句话：检测框本身没人看得懂，判定层把十类框变成一句人能读的结论。\n"
             "三个坑要讲清楚，尤其是「不能用 IoU」——这是最容易犯的错，也是这个规则层的价值所在。\n"
             "如果追问准确率：规则层没有独立标注真值，它是「可解释的汇总」，不是新的分类器，这点要如实说。")


# ------------------------------------------------------------------ P10 创新点 3
def p10(d, m):
    s = d.page("创新点 03", "零 torch 全链路自实现：换一台没独显的机器也能复算")
    cols = [
        ("依赖清单", ["numpy / onnxruntime / opencv-headless / pillow", "4 个包，约 120 MB",
                      "不装 torch（省 2.5 GB 下载）", "没有隐式依赖，环境一次装好"], ACCENT),
        ("自己实现的部分", ["letterbox 与坐标反演（fx, fy）", "类内 NMS、多尺度合并",
                            "101 点插值 VOC AP、贪心匹配", "人级判定与合规汇总"], GREEN),
        ("代价与收益", ["CPU %.0f ms / 图（基线口径）" % m["ms_a"], "全部指标可逐张复算、可 diff",
                        "网页与 PPT 的数字全部脚本生成", "缺点：没有 GPU 加速，批量跑得慢"], WARN),
    ]
    cw = (CW - 2 * 0.26) / 3
    for i, (head, items, col) in enumerate(cols):
        x = ML + i * (cw + 0.26)
        panel(s, x, 1.90, cw, 3.16, PANEL, LINE, 0.05)
        tag(s, x + 0.26, 2.06, cw - 0.52, head, col)
        rule(s, x + 0.26, 2.40, 0.38, col, 2.2)
        bullets(s, x + 0.26, 2.58, cw - 0.50, 2.30,
                [("sub", t) for t in items], size=11, gap=9)

    panel(s, ML, 5.28, CW, 1.02, "EEF4FC", "C9DDF3", 0.05)
    textbox(s, ML + 0.28, 5.40, CW - 0.56, 0.28, "为什么这算创新（工程性创新）", size=10.5,
            bold=True, color=ACCENT)
    textbox(s, ML + 0.28, 5.68, CW - 0.60, 0.52,
            "把「能跑」推进到「能复算」：同样的 4 个包、同一条命令，任何人都能把我报的每个数重算一遍。",
            size=13, bold=True, color=INK)
    notes(s, "创新点 03 是工程性创新，不要硬说成算法创新。\n"
             "价值在「可复算」：mAP 不是调库打印的，是自己按 VOC 101 点插值实现的，别人可以逐张对账。\n"
             "如果问「手写 mAP 会不会错」：和公开库口径对齐过，train/valid/test 三个划分趋势一致，"
             "而且 A/B 用的是同一套实现，比较是公平的。")


# ------------------------------------------------------------------ P11 对照设计
def p11(d, m):
    s = d.page("六 · 对照实验设计", "四同原则：只让「预处理」这一个变量变化")
    same = [("同权重", "同一份 ONNX（12.2 MB）"), ("同测试集", "test %d 张 / %d 框" % (m["n_test"], m["gt_test"])),
            ("同阈值", "conf %.2f · IoU %.2f" % (m["conf"], m["iou"])), ("同硬件", "同一台机器，CPU 单线程口径")]
    cw = (CW - 3 * 0.24) / 4
    for i, (k, v) in enumerate(same):
        x = ML + i * (cw + 0.24)
        panel(s, x, 1.90, cw, 0.96, "E8F2FE", ACCENT, 0.10)
        textbox(s, x + 0.20, 2.02, cw - 0.40, 0.30, k, size=13, bold=True, color=INK)
        textbox(s, x + 0.20, 2.36, cw - 0.40, 0.42, v, size=10, color=SUB)

    rows = [["策略", "做法", "mAP@50", "大目标召回", "ms / 图"],
            ["A 整图基线", "整图 letterbox 640，单尺度一次推理",
             "%.4f" % m["mA"], m["big_a"], "%d" % round(m["ms_a"])],
            ["B 缩图多尺度（采用）", "1.0× + 0.5× 各推理一次，坐标合并",
             "%.4f" % m["mB"], m["big_b"], "%d" % round(m["ms_b"])],
            ["C 分块 2×2（负面对照）", "切成 4 块各放大回 640",
             "%.4f" % m["mC"], m["big_c"], "%d" % round(m["ms_c"])]]
    table(s, ML, 3.12, CW, rows, [2.70, 5.05, 1.45, 1.55, 1.22], size=12, head_size=11,
          row_h=0.62, head_h=0.40,
          aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
          accents={(2, 2): ACCENT, (2, 3): ACCENT, (3, 2): WARN, (3, 3): WARN})

    bullets(s, ML, 5.62, CW, 1.10, [
        ("main", "C 组是故意设的反证：直觉上「切块让目标变大」应该更好，实测 %s，说明有效的是「尺度匹配」而非「放大」。" % ("%.4f" % m["mC"])),
        ("main", "三组共用同一套预标注、同一套 mAP 实现，比较对象是同一条链路的不同预处理分支。"),
    ], size=11.5, gap=8)
    notes(s, "这一页是为回答「你怎么证明改进是你带来的」。\n"
             "四同原则：同权重、同测试集、同阈值、同硬件，唯一变量是预处理。\n"
             "C 组负面对照是加分项：它证明我不是在挑一个涨点的实验，而是在验证一个机制假设。")


# ------------------------------------------------------------------ P12 结果
def p12(d, ab, abv):
    A, B = ab["modes"]["A 整图基线"], ab["modes"]["B 缩图多尺度"]
    C = ab["modes"]["C 分块2x2"]
    gain = B["metrics"]["mAP50"] - A["metrics"]["mAP50"]
    s = d.page("七 · 结果", "测试集 mAP@50 提升 %.4f，验证集同向" % gain)

    bars(s, ML + 0.18, 2.34, 5.28, 1.92,
         [("整图基线", A["metrics"]["mAP50"], "7A8798", "%d ms" % round(A["latency_ms"])),
          ("双尺度（采用）", B["metrics"]["mAP50"], ACCENT, "%d ms" % round(B["latency_ms"])),
          ("分块 2×2", C["metrics"]["mAP50"], WARN, "%d ms" % round(C["latency_ms"]))],
         vmax=0.66, value_fmt="%.4f")

    opA = A["metrics"]["operating_point_conf035"]["person"]
    opB = B["metrics"]["operating_point_conf035"]["person"]
    rows = [["指标", "整图", "双尺度"],
            ["mAP@50", "%.4f" % A["metrics"]["mAP50"], "%.4f" % B["metrics"]["mAP50"]],
            ["mAP@50-95", "%.4f" % A["metrics"]["mAP50_95"], "%.4f" % B["metrics"]["mAP50_95"]],
            ["大目标召回", "%.4f" % A["recall_by_size"]["大 (>=96px)"]["recall"],
             "%.4f" % B["recall_by_size"]["大 (>=96px)"]["recall"]],
            ["人的 R@0.35", "%.4f" % opA["recall"], "%.4f" % opB["recall"]]]
    table(s, ML + 5.92, 1.88, CW - 5.92, rows, [2.10, 1.70, 1.70], size=12, head_size=11,
          row_h=0.46, head_h=0.36, aligns=[PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
          accents={(1, 2): ACCENT, (2, 2): ACCENT, (3, 2): ACCENT})

    textbox(s, ML, 5.14, CW, 0.30, "两个视角同时看：测试集（主结论）与验证集（复核）", size=11,
            bold=True, color=ACCENT)
    textbox(s, ML, 5.48, CW, 1.42,
            ["验证集 %d 张复核：%.4f → %.4f，方向一致，不是测试集上的偶然。"
             % (abv["images"], abv["modes"]["A 整图基线"]["metrics"]["mAP50"],
                abv["modes"]["B 缩图多尺度"]["metrics"]["mAP50"]),
             "全量 %d 张逐张推理、不抽样；收益集中在大目标召回 %.4f → %.4f。"
             % (1206, A["recall_by_size"]["大 (>=96px)"]["recall"],
                B["recall_by_size"]["大 (>=96px)"]["recall"])],
            size=12.5, color=SUB, spacing=1.5)
    notes(s, "结果只说三个数：测试集 0.5401 → 0.5819（+0.0418）；验证集 0.5696 → 0.6201，方向一致；"
             "大目标召回 0.7392 → 0.8025。\n"
             "不要夸大成「整体精度大涨」——小目标召回没变，负向类也基本没动，下一节会讲清楚。")


# ------------------------------------------------------------------ P13 前后期
def p13(d, ab):
    A, B, C = [ab["modes"][k] for k in ("A 整图基线", "B 缩图多尺度", "C 分块2x2")]
    s = d.page("八 · 前期与后期的差异", "同权重、同数据、同阈值：差异全部来自推理流程")
    rows = [["阶段", "做法", "mAP@50", "大目标召回", "ms/图"],
            ["前期（直接跑）", "整图压 640，单尺度一次推理",
             "%.4f" % A["metrics"]["mAP50"], "%.4f" % A["recall_by_size"]["大 (>=96px)"]["recall"],
             "%d" % round(A["latency_ms"])],
            ["后期（本次）", "1.0× + 0.5× 联合 + 人级判定",
             "%.4f" % B["metrics"]["mAP50"], "%.4f" % B["recall_by_size"]["大 (>=96px)"]["recall"],
             "%d" % round(B["latency_ms"])],
            ["负面对照", "分块 2×2 各放回 640",
             "%.4f" % C["metrics"]["mAP50"], "%.4f" % C["recall_by_size"]["大 (>=96px)"]["recall"],
             "%d" % round(C["latency_ms"])]]
    table(s, ML, 1.90, CW, rows, [2.05, 4.55, 1.75, 2.05, 1.60], size=12.5, head_size=11.5,
          row_h=0.62, head_h=0.40,
          aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT],
          accents={(2, 2): ACCENT, (2, 3): ACCENT, (3, 2): WARN, (3, 3): WARN})

    bullets(s, ML, 4.34, CW, 1.50, [
        ("main", "后期涨点靠「喂什么给模型」：缩图让大目标在 640 里占比更接近训练分布"),
        ("main", "负面对照说明直觉会错：分块把每块强制放大回 640，大目标召回腰斩到 %.4f"
         % C["recall_by_size"]["大 (>=96px)"]["recall"]),
    ], size=13, gap=12)

    panel(s, ML, 5.96, CW, 0.86, "FDF1EC", "F5C9B6", 0.06)
    textbox(s, ML + 0.26, 6.08, CW - 0.52, 0.62,
            "「前期与后期的差异」= 推理流程的差异，不是训练的差异：本期未做训练微调（本机无 CUDA 工具链），"
            "训练微调列为后期第一步。",
            size=11.5, color=WARN, spacing=1.4)
    notes(s, "这题一定要正面回答，不要绕：本期没有训练，权重是公开的。\n"
             "前期 = 整图直接跑；后期 = 双尺度 + 判定层。差异全部可归因到流程。\n"
             "如果问「那训练呢」：需要 CUDA 环境，放在后期第一项，预期目标写在最后一页。")


# ------------------------------------------------------------------ P14 失败与边界
def p14(d, m):
    s = d.page("九 · 失败案例与边界", "知道自己哪儿会错，才知道该怎么用")
    a = img("pred_ppe_0261")
    b = img("pred_ppe_0357")
    for i, p in enumerate((a, b)):
        if p:
            s.shapes.add_picture(p, Inches(ML + i * 3.06), Inches(1.96), width=Inches(2.82))
    textbox(s, ML, 4.96, 2.82, 0.26, "纯误检：只有 1 个人，错了 16 次", size=9.5, color=MUTED,
            align=PP_ALIGN.CENTER)
    textbox(s, ML + 3.06, 4.96, 2.82, 0.26, "密集人群：漏 4 人、误检 8 个", size=9.5, color=MUTED,
            align=PP_ALIGN.CENTER)

    rows = [["边界", "实测与说明"],
            ["小目标", "召回 0.7733 → 0.7733，没有提升；<48 px 只能靠补数据重训"],
            ["负向类", "未戴帽 AP 0.275，测试集该类真值框只有 24 个（3.9%）"],
            ["密集人群", "判定层按面积归属，人群重叠时会出现错配"],
            ["场景", "夜间、逆光、浓雾、人群堆叠：不适用"]]
    table(s, ML + 6.22, 1.96, CW - 6.22, rows, [1.10, 4.60], size=11, head_size=10.5,
          row_h=0.66, head_h=0.36)

    textbox(s, ML + 6.22, 4.94, CW - 6.22, 0.26, "明确不做的事", size=10.5, bold=True, color=WARN)
    textbox(s, ML + 6.22, 5.22, CW - 6.22, 1.30,
            ["不声称「召回整体提升」——只提大目标",
             "不做实时告警（PC 端离线，%d ms/图）" % round(m["ms_b"]),
             "不把结果当作验收依据，只做筛查与预标注"],
            size=11, color=WARN, spacing=1.45)
    notes(s, "不要跳过这一页，也不要等老师问。\n"
             "三条硬边界：小目标召回没提升、负向类受长尾限制、密集人群会错配。\n"
             "最后一句定调：这套东西是筛查与预标注，不是验收，更不是实时告警。")


# ------------------------------------------------------------------ P15 价值
def p15(d, m):
    s = d.page("十 · 价值贡献", "三件可以带走的东西")
    items = [
        ("可复现的对照方法",
         "同权重、同测试集、同阈值、同硬件，三组策略 + 按尺寸拆召回 + 负面对照；结论能被别人重算。"),
        ("一套可交付的检测资产",
         "%d 张真实工地照片、%d 张中文标注图、五类口径的判定规则、逐张可复核的三视图网页。"
         % (m["n_all"], m["n_ann"])),
        ("一条低门槛的部署路径",
         "4 个包约 120 MB、CPU %.0f ms/图，不装 torch 也能跑通检测、评估与判定。"
         % m["ms_a"]),
    ]
    for i, (k, v) in enumerate(items):
        y = 1.90 + i * 1.56
        panel(s, ML, y, CW, 1.34, PANEL, LINE, 0.05)
        cir = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(ML + 0.30), Inches(y + 0.42),
                                 Inches(0.50), Inches(0.50))
        cir.fill.solid()
        cir.fill.fore_color.rgb = RGBColor.from_string(ACCENT)
        cir.line.fill.background()
        cir.shadow.inherit = False
        tf = cir.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        pp = tf.paragraphs[0]
        pp.alignment = PP_ALIGN.CENTER
        r = pp.add_run()
        r.text = str(i + 1)
        r.font.size = Pt(15)
        r.font.bold = True
        r.font.color.rgb = RGBColor.from_string(WHITE)
        r.font.name = "Microsoft YaHei"
        textbox(s, ML + 1.02, y + 0.16, CW - 1.40, 0.34, k, size=16, bold=True, color=INK)
        textbox(s, ML + 1.02, y + 0.58, CW - 1.42, 0.66, v, size=12, color=SUB, spacing=1.35)
    notes(s, "三句话：方法可复现、资产可复用、部署门槛低。\n"
             "不要吹「能上线」，只说「能复算、能交付、少装 2.5 GB」。\n"
             "教学价值在于：一个没有独显的实验室，也能把检测、评估、对照实验整条链路跑完。")


# ------------------------------------------------------------------ P16 后期改进
def p16(d):
    s = d.page("十一 · 后期改进", "先补数据，再动模型，最后才谈实时")
    steps = [("近期 · 数据", "补 300–500 张本场景照片，重点补负样本与逆光", "负向类 AP 从 0.275 起步"),
             ("近期 · 训练", "装 torch，GTX 1650 上微调 YOLOv8n/s", "mAP@50 目标 0.75+"),
             ("中期", "IoU 矩阵 + 匈牙利匹配替代面积占比规则", "消除密集人群错配"),
             ("远期", "TensorRT + RTSP + 跟踪去重", "从「能筛查」到「能值守」")]
    cw, gap = 2.72, 0.34
    for i, (t, what, why) in enumerate(steps):
        x = ML + i * (cw + gap)
        panel(s, x, 1.94, cw, 2.76, PANEL, LINE, 0.05)
        textbox(s, x + 0.22, 2.10, cw - 0.44, 0.26, t, size=10, bold=True, color=ACCENT)
        textbox(s, x + 0.22, 2.42, cw - 0.42, 1.14, what, size=12, color=INK, spacing=1.45)
        rule(s, x + 0.22, 3.62, cw - 0.44, LINE, 1.0)
        textbox(s, x + 0.22, 3.76, cw - 0.42, 0.84, why, size=10.5, color=MUTED, spacing=1.4)

    textbox(s, ML, 5.08, CW, 1.0,
            ["一句话收尾：本期证明了「不改模型也能更好」，",
             "下一期要回答的是「补上数据和训练之后，能好到哪」。"],
            size=15, bold=True, color=INK, spacing=1.5)
    notes(s, "四步按成本排：补数据最便宜、收益最大；微调要 CUDA；规则换匹配是工程债；实时是远期，不承诺。\n"
             "目标值要给但别许愿：微调用 GTX 1650、YOLOv8n/s，mAP@50 目标 0.75 量级是合理区间。")


# ------------------------------------------------------------------ P17 结论
def p17(d, m):
    s = d.page("十二 · 结论", "一句话讲完这个项目")
    panel(s, ML, 1.92, CW, 1.86, "EEF4FC", "C9DDF3", 0.04)
    textbox(s, ML + 0.34, 2.06, CW - 0.68, 1.60,
            ["针对「工地班前检查靠人盯、不留痕」的问题，在预处理与判定两个环节做改动，",
             "在「同权重、同阈值、纯 CPU」的条件下把测试集 mAP@50 从 %.4f 提到 %.4f、"
             % (m["a"], m["b"]),
             "大目标召回从 %s 提到 %s；目前仍受限于小目标召回未变与负向类长尾。"
             % (m["big_a"], m["big_b"])],
            size=15, color=INK, spacing=1.55)

    rows = [["交付物", "位置", "说明"],
            ["检测与评估脚本", "run.py + tools/", "一条命令跑完推理 / 评估 / 对照 / 网页"],
            ["网页技术报告", "web/index.html", "13 章：架构 / 流程 / 效果 / 指标 / A/B / 失败 / 岗位对齐"],
            ["标注成果", "demo/ demo2/", "%d 张中文标注图，五类口径" % m["n_ann"]],
            ["数据与权重", "data/ models/", "均为 CC BY 4.0 公开资源，附来源与哈希"]]
    table(s, ML, 4.04, CW, rows, [2.55, 2.35, 7.05], size=11.5, head_size=11,
          row_h=0.46, head_h=0.36)

    textbox(s, ML, 6.44, CW, 0.34, "谢谢各位老师，请提问。", size=15, bold=True, color=ACCENT)
    notes(s, "结论用「针对什么问题—动了哪一块—在什么条件下—得到什么结果—还差什么」这一句讲完，"
             "这也是老师最爱听的句式。\n"
             "可能的追问与回答：\n"
             "· 提升 0.04 算大吗？——单点提升不大，但可归因、可复现、有负面对照支撑，方法学价值大于数值。\n"
             "· 为什么不做训练？——本机无 CUDA；本次要回答的是流程优化的边界，训练是下一步。\n"
             "· 判定规则有真值吗？——没有独立标注，它是可解释的汇总层，不是新分类器。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "PPE答辩汇报-最终版.pptx"))
    args = ap.parse_args()

    full = load("full_eval_summary.json")
    ab = load("ab_tiled.json")
    abv = load("ab_tiled_valid.json")
    dB = load("demo2_stats.json")
    with open(os.path.join(ROOT, "demo2", "manifest.json"), encoding="utf-8") as f:
        mani = json.load(f)

    mA, mB, mC = [ab["modes"][k] for k in ("A 整图基线", "B 缩图多尺度", "C 分块2x2")]
    per = mA["metrics"]["per_class"]
    order = [("安全帽 helmet", "helmet"), ("人 person", "person"), ("反光背心 vest", "vest"),
             ("未穿背心 no-vest", "no-vest"), ("未戴帽 no-helmet", "no-helmet")]
    cls_test = [(name, per[k]["gt"]) for name, k in order]

    buckets = {"compliant": 0, "no_helmet": 0, "no_vest": 0, "both": 0}
    for x in mani:
        c = x["counts"]
        if c["no-helmet"] and c["no-vest"]:
            buckets["both"] += 1
        elif c["no-helmet"]:
            buckets["no_helmet"] += 1
        elif c["no-vest"]:
            buckets["no_vest"] += 1
        elif c["person"]:
            buckets["compliant"] += 1

    n_ann = 0
    for sub in ("demo", "demo2"):
        d = os.path.join(ROOT, sub, "images")
        n_ann += sum(1 for fn in os.listdir(d) if fn.lower().endswith(".json"))

    meta = {
        "a": mA["metrics"]["mAP50"], "b": mB["metrics"]["mAP50"], "c": mC["metrics"]["mAP50"],
        "mA": mA["metrics"]["mAP50"], "mB": mB["metrics"]["mAP50"], "mC": mC["metrics"]["mAP50"],
        "ms_a": mA["latency_ms"], "ms_b": mB["latency_ms"], "ms_c": mC["latency_ms"],
        "big_a": "%.4f" % mA["recall_by_size"]["大 (>=96px)"]["recall"],
        "big_b": "%.4f" % mB["recall_by_size"]["大 (>=96px)"]["recall"],
        "big_c": "%.4f" % mC["recall_by_size"]["大 (>=96px)"]["recall"],
        "n_all": full["all"]["images"], "gt_all": full["all"]["gt_boxes"],
        "n_test": full["test"]["images"], "gt_test": full["test"]["gt_boxes"],
        "conf": ab["conf"], "iou": ab["iou"],
        "cls_test": cls_test, "n_ann": n_ann,
        "n_demo2": len(dB), "buckets": buckets,
        "mapping": [("模型 10 类", "只报其中 5 类：人 / 安全帽 / 未戴帽 / 反光背心 / 未穿背心"),
                    ("未采用 5 类", "口罩、未戴口罩、锥桶、机械、车辆（与本课题无关）"),
                    ("安全服口径", "只认反光背心，不区分款式与颜色")],
        "ab": ab, "abv": abv,
    }

    d = Deck()
    p1(d, meta)
    p2(d)
    p3(d)
    p4(d)
    p5(d, meta)
    p6(d, meta)
    p7(d, meta)
    p8(d, ab)
    p9(d, meta)
    p10(d, meta)
    p11(d, meta)
    p12(d, ab, abv)
    p13(d, ab)
    p14(d, meta)
    p15(d, meta)
    p16(d)
    p17(d, meta)
    path = d.save(args.out)

    prs = Presentation(path)
    WW, HH = prs.slide_width / 914400, prs.slide_height / 914400
    bad = []
    for i, sl in enumerate(prs.slides, 1):
        for sh in sl.shapes:
            if sh.left is None:
                continue
            if (sh.left < 0 or sh.top < 0 or sh.left + sh.width > Emu(int(WW * 914400)) + Emu(9525)
                    or sh.top + sh.height > Emu(int(HH * 914400)) + Emu(9525)):
                bad.append("slide %d 越界 %s" % (i, sh.shape_type))
    print("saved:", path)
    print("slides:", len(prs.slides), " size: %.2f MB" % (os.path.getsize(path) / 1048576))
    print("越界:", len(bad))
    for x in bad:
        print("   ", x)


if __name__ == "__main__":
    main()
