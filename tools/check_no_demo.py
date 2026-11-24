# -*- coding: utf-8 -*-
"""扫描 PPT 全文（含备注）里不该出现的「演示 / 时长」类字样。"""
import sys

from pptx import Presentation

BAD = ["演示", "⏱", "分钟", "双击", "超时", "只演", "快捷方式", "课堂", "汇报时间", "开口器"]


def main(path):
    prs = Presentation(path)
    hits = []
    for i, sl in enumerate(prs.slides, 1):
        texts = []
        for sh in sl.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                texts.append(sh.text_frame.text)
            if sh.has_table:
                for r in sh.table.rows:
                    for c in r.cells:
                        if c.text.strip():
                            texts.append(c.text)
        if sl.has_notes_slide:
            texts.append("[备注] " + sl.notes_slide.notes_text_frame.text)
        for t in texts:
            for w in BAD:
                if w in t:
                    hits.append((i, w, t.strip().replace("\n", " / ")[:90]))
    print("slides:", len(prs.slides), " hits:", len(hits))
    for i, w, t in hits:
        print("  s%02d [%s] %s" % (i, w, t))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/PPE答辩汇报-最终版.pptx"))
