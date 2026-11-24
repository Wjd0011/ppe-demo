# -*- coding: utf-8 -*-
"""PPT 排版工具集（颜色、文本框、表格、装饰与 Deck 框架）。

被 build_ppt_final.py 复用；只放与具体页面无关的东西。
"""
import json
import os

from pptx import Presentation
from pptx.chart.data import CategoryChartData  # noqa: F401  (保留给后续加原生图表)
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "Microsoft YaHei"
MONO = "Consolas"

INK = "0F1B2D"
SUB = "5A6675"
MUTED = "8A97A6"
ACCENT = "1E7FE0"
WARN = "E4572E"
GREEN = "2E9E5B"
LINE = "D8DEE7"
PANEL = "F4F7FB"
WHITE = "FFFFFF"

W, H = 13.333, 7.5
ML, MR = 0.68, 0.68
CW = W - ML - MR          # 内容区宽度 11.973


# ---------------------------------------------------------------- 基础工具
def load(name):
    with open(os.path.join(ROOT, "out", name), encoding="utf-8") as f:
        return json.load(f)


def count_boxes(sub):
    """直接数标注 JSON 里的 shapes，避免与 stats 口径混淆。"""
    total, files = 0, 0
    d = os.path.join(ROOT, sub, "images")
    for fn in os.listdir(d):
        if not fn.lower().endswith(".json"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            total += len(json.load(f).get("shapes", []))
        files += 1
    return total


def set_font(run, size=15, bold=False, color=INK, font=FONT, italic=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.name = font
    f.color.rgb = RGBColor.from_string(color)
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", font)


def textbox(slide, x, y, w, h, text="", size=15, bold=False, color=INK,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT,
            spacing=1.25, margins=(0, 0, 0, 0)):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left, tf.margin_right, tf.margin_top, tf.margin_bottom = [Inches(m) for m in margins]
    lines = text if isinstance(text, (list, tuple)) else [text]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = ln
        set_font(r, size, bold, color, font)
    return tb


def bullets(slide, x, y, w, h, items, size=15, gap=10, spacing=1.28):
    """items: (level, text[, bold]) level in {'main','sub'}"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, item in enumerate(items):
        level, text = item[0], item[1]
        bold = item[2] if len(item) > 2 else False
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = spacing
        p.space_after = Pt(gap)
        pPr = p._p.get_or_add_pPr()
        if level == "sub":
            pPr.set("marL", str(int(Inches(0.30))))
            pPr.set("indent", str(int(-Inches(0.30))))
            mrk, mcol, fsz, tcol = "–", MUTED, size - 2, SUB
        else:
            pPr.set("marL", str(int(Inches(0.26))))
            pPr.set("indent", str(int(-Inches(0.26))))
            mrk, mcol, fsz, tcol = "▪", ACCENT, size, INK
        r0 = p.add_run()
        r0.text = mrk + "  "
        set_font(r0, fsz, True, mcol)
        r1 = p.add_run()
        r1.text = text
        set_font(r1, fsz, bold, tcol)
    return tb


def panel(slide, x, y, w, h, fill=PANEL, line=LINE, radius=0.03, dash=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.adjustments[0] = radius
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(fill)
    if line:
        shp.line.color.rgb = RGBColor.from_string(line)
        shp.line.width = Pt(1)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    shp.text_frame.word_wrap = True
    return shp


def rule(slide, x, y, w, color=ACCENT, thick=3.2):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Pt(thick))
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(color)
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


# ---------------------------------------------------------------- 表格
NO_STYLE_NO_GRID = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"


def _border(cell, color=LINE, w=9525):
    tcPr = cell._tc.get_or_add_tcPr()
    for i, e in enumerate(("L", "R", "T", "B")):
        tag = "a:ln%s" % e
        old = tcPr.find(qn(tag))
        if old is not None:
            tcPr.remove(old)
        ln = tcPr.makeelement(qn(tag), {"w": str(w), "cap": "flat", "cmpd": "sng", "algn": "ctr"})
        fill = ln.makeelement(qn("a:solidFill"), {})
        clr = fill.makeelement(qn("a:srgbClr"), {"val": color})
        fill.append(clr)
        ln.append(fill)
        tcPr.insert(i, ln)


def cell_text(cell, text, size=12, bold=False, color=INK, align=PP_ALIGN.LEFT, font=FONT):
    cell.text = ""
    tf = cell.text_frame
    tf.word_wrap = True
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.margin_left = Inches(0.09)
    cell.margin_right = Inches(0.09)
    cell.margin_top = Inches(0.02)
    cell.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = str(text)
    set_font(r, size, bold, color, font)


def table(slide, x, y, w, rows, col_w, size=12, head_size=11.5,
          header_fill=INK, header_color=WHITE, row_h=0.34, head_h=0.36,
          aligns=None, zebra=PANEL, accents=None):
    """rows[0] 表头；col_w 为英寸列表；accents = {(r,c): color}"""
    nrow, ncol = len(rows), len(rows[0])
    gf = slide.shapes.add_table(nrow, ncol, Inches(x), Inches(y), Inches(w), Inches(head_h + row_h * (nrow - 1)))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = tblPr.makeelement(qn("a:tableStyleId"), {})
        tblPr.append(sid)
    sid.text = NO_STYLE_NO_GRID
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    tbl.rows[0].height = Inches(head_h)
    for i in range(1, nrow):
        tbl.rows[i].height = Inches(row_h)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            al = PP_ALIGN.LEFT
            if aligns and j < len(aligns):
                al = aligns[j]
            if i == 0:
                c.fill.solid()
                c.fill.fore_color.rgb = RGBColor.from_string(header_fill)
                cell_text(c, val, head_size, True, header_color, al)
            else:
                c.fill.solid()
                c.fill.fore_color.rgb = RGBColor.from_string(zebra if i % 2 == 0 else WHITE)
                col = INK
                bold = False
                if accents and (i, j) in accents:
                    col = accents[(i, j)]
                    bold = True
                cell_text(c, val, size, bold, col, al)
            _border(c)
    return tbl


# ---------------------------------------------------------------- 柱状图（手绘）
def bars(slide, x, y, w, h, items, vmax, unit="", value_fmt="%.4f"):
    """items: [(label, value, color, note)]"""
    base_y = y + h
    axis = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(base_y), Inches(w), Pt(1.2))
    axis.fill.solid()
    axis.fill.fore_color.rgb = RGBColor.from_string(LINE)
    axis.line.fill.background()
    axis.shadow.inherit = False
    n = len(items)
    slot = w / n
    bw = min(1.05, slot * 0.44)
    for i, (label, val, color, note) in enumerate(items):
        cx = x + slot * (i + 0.5)
        bh = max(0.02, (val / vmax) * h)
        shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(cx - bw / 2), Inches(base_y - bh), Inches(bw), Inches(bh))
        shp.adjustments[0] = 0.06
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor.from_string(color)
        shp.line.fill.background()
        shp.shadow.inherit = False
        textbox(slide, cx - 0.75, base_y - bh - 0.42, 1.5, 0.3, value_fmt % val,
                size=13, bold=True, color=color, align=PP_ALIGN.CENTER)
        textbox(slide, cx - 0.9, base_y + 0.10, 1.8, 0.3, label, size=11.5, color=SUB, align=PP_ALIGN.CENTER)
        if note:
            textbox(slide, cx - 0.9, base_y + 0.40, 1.8, 0.28, note, size=10.5, color=MUTED, align=PP_ALIGN.CENTER)


# ---------------------------------------------------------------- 页面框架
class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = Inches(W)
        self.prs.slide_height = Inches(H)
        self.blank = self.prs.slide_layouts[6]
        self.n = 0

    def page(self, kicker, title, total=None):
        s = self.prs.slides.add_slide(self.blank)
        self.n += 1
        textbox(s, ML, 0.42, CW, 0.28, kicker, size=10.5, bold=True, color=ACCENT)
        textbox(s, ML, 0.68, CW, 0.62, title, size=27, bold=True, color=INK, spacing=1.1)
        rule(s, ML, 1.40, 0.92)
        # 页脚
        textbox(s, ML, 7.06, 6.2, 0.26, "施工场地安全帽 / 反光背心检测 · 答辩汇报", size=9.5, color=MUTED)
        textbox(s, W - MR - 1.2, 7.06, 1.2, 0.26, "%02d" % self.n, size=9.5, color=MUTED, align=PP_ALIGN.RIGHT)
        return s

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.prs.save(path)
        return path


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text
