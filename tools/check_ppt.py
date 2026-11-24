# -*- coding: utf-8 -*-
"""检查生成的 PPT 是否存在文字溢出、重叠、越界。

无渲染引擎可用（本机无 LibreOffice），因此用字体度量做启发式估算：
  · CJK / 全角字符按 1.00 em 计宽，ASCII 按 0.52 em，数字/标点按 0.55 em
  · 逐段按框宽折行，行高 = size * line_spacing
  · 需要高度 > 框高 * 1.02 判为溢出
另外检查：形状越出页面、文本框互相重叠且都含文字。
"""
import math
import sys

from pptx import Presentation
from pptx.util import Emu

EMU = 914400.0
TOL = 1.02          # 允许 2% 的度量误差
OVERLAP_MIN = 0.12  # 重叠面积 / 较小面积


def char_w(ch):
    o = ord(ch)
    if ch == " ":
        return 0.28
    if o < 128:
        if ch.isdigit():
            return 0.55
        if ch.isalpha():
            return 0.52
        return 0.42
    if 0x2E80 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFF60 or 0x3000 <= o <= 0x303F:
        return 1.0
    if 0x2460 <= o <= 0x24FF:   # ①②③
        return 1.0
    return 0.72


def wrap_lines(text, size, width_in):
    """估算折行后行数。width_in 为可用宽度（英寸）。"""
    if not text:
        return 1
    per_line_pt = width_in * 72.0
    lines, cur = 1, 0.0
    for ch in text:
        w = char_w(ch) * size
        if cur + w > per_line_pt:
            lines += 1
            cur = w
        else:
            cur += w
    return lines


def need_height(shape):
    tf = shape.text_frame
    size_avail = shape.width / EMU
    ml = (tf.margin_left or 0) / EMU
    mr = (tf.margin_right or 0) / EMU
    width_in = max(0.15, size_avail - ml - mr)
    total = 0.0
    for p in tf.paragraphs:
        txt = "".join(r.text for r in p.runs)
        sizes = [r.font.size.pt for r in p.runs if r.font.size is not None]
        size = max(sizes) if sizes else 18.0
        ls = p.line_spacing if isinstance(p.line_spacing, float) else 1.2
        n = wrap_lines(txt, size, width_in)
        total += n * size * ls * 1.02
        sa = p.space_after
        total += sa.pt if sa is not None else 0.0
        sb = p.space_before
        total += sb.pt if sb is not None else 0.0
    return total / 72.0


def rect(sh):
    return (sh.left / EMU, sh.top / EMU,
            (sh.left + sh.width) / EMU, (sh.top + sh.height) / EMU)


def overlap(a, b):
    x = min(a[2], b[2]) - max(a[0], b[0])
    y = min(a[3], b[3]) - max(a[1], b[1])
    if x <= 0 or y <= 0:
        return 0.0
    inter = x * y
    sa = (a[2] - a[0]) * (a[3] - a[1])
    sb = (b[2] - b[0]) * (b[3] - b[1])
    small = min(sa, sb)
    return inter / small if small > 0 else 0.0


def main(path):
    prs = Presentation(path)
    W, H = prs.slide_width / EMU, prs.slide_height / EMU
    bad = []
    for i, sl in enumerate(prs.slides, 1):
        boxes = []
        pics = []
        for sh in sl.shapes:
            if sh.left is None:
                continue
            r = rect(sh)
            if r[0] < -0.02 or r[1] < -0.02 or r[2] > W + 0.02 or r[3] > H + 0.02:
                bad.append((i, "越界", "%.2f,%.2f → %.2f,%.2f" % r, getattr(sh, "name", "")))
            if sh.has_text_frame and sh.text_frame.text.strip():
                nh = need_height(sh)
                avail = sh.height / EMU
                if nh > avail * TOL:
                    bad.append((i, "文字溢出", "需 %.2f\" / 有 %.2f\"：%s"
                                % (nh, avail, sh.text_frame.text.strip()[:34].replace("\n", " / ")),
                                getattr(sh, "name", "")))
                boxes.append((r, sh.text_frame.text.strip()[:24]))
            elif sh.shape_type == 13:      # PICTURE
                pics.append((r, getattr(sh, "name", "")))
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                ov = overlap(boxes[a][0], boxes[b][0])
                if ov > OVERLAP_MIN:
                    bad.append((i, "文本框重叠 %.0f%%" % (ov * 100),
                                "%s ⇄ %s" % (boxes[a][1], boxes[b][1]), ""))
        # 图片与文字互相压盖：只报「文字大部分压在图上」
        for (pr, pname) in pics:
            for (br, btxt) in boxes:
                ov = overlap(pr, br)
                if ov > 0.5:
                    bad.append((i, "文字压图 %.0f%%" % (ov * 100), "%s ↔ %s" % (pname, btxt), ""))
    print("slides:", len(prs.slides))
    print("issues:", len(bad))
    for i, kind, detail, name in bad:
        print("  s%02d %-14s %s" % (i, kind, detail))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/PPE答辩汇报-最终版.pptx"))
