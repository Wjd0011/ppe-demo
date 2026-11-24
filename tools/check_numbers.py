# -*- coding: utf-8 -*-
"""Cross-check the numbers rendered into web/index.html against the source JSON."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def j(name):
    with open(os.path.join(ROOT, "out", name), encoding="utf-8") as f:
        return json.load(f)


def main():
    h = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
    full = j("full_eval_summary.json")
    m = j("metrics.json")
    sc = j("split_counts.json")

    print("== split rows in page ==")
    for sp, cn in [("train", "训练集"), ("valid", "验证集"), ("test", "测试集")]:
        v = full[sp]
        pat = r"<tr[^>]*><td>%s</td><td class='num'>(\d+)</td><td class='num'>(\d+)</td>" \
              r"<td class='num'>(\d+)</td><td class='num'><b>([\d.]+)</b></td>" % cn
        mm = re.search(pat, h)
        ok = mm and mm.group(1) == str(v["images"]) and mm.group(2) == str(v["gt_boxes"]) \
            and mm.group(3) == str(v["pred_boxes"]) and abs(float(mm.group(4)) - v["mAP50"]) < 1e-6
        print("%-4s rendered=%s source=%s -> %s" % (
            sp, mm.groups() if mm else None,
            (v["images"], v["gt_boxes"], v["pred_boxes"], v["mAP50"]), "OK" if ok else "MISMATCH"))

    print("== kpis ==")
    print("mAP(all) in page:", "%.4f" % full["all"]["mAP50"], "->", ("%.4f" % full["all"]["mAP50"]) in h)
    print("mAP(test) in page:", "%.4f" % m["mAP50"], "->", ("%.4f" % m["mAP50"]) in h)
    print("total imgs:", full["all"]["images"], "->", str(full["all"]["images"]) in h)

    print("== dataset table ==")
    tot_imgs = sum(sc[s]["labels"] for s in ("train", "valid", "test"))
    tot = [sum(sc[s]["counts"][i] for s in ("train", "valid", "test")) for i in range(5)]
    print("source:", tot_imgs, tot)
    for sp in ("train", "valid", "test"):
        seg = "<td>%s</td><td class='num'>%d</td>" % (sp, sc[sp]["labels"])
        print(" ", sp, "->", seg in h)

    print("== failure gallery ==")
    fs = j("failure_stats.json")
    print("cards:", len(fs), "->", h.count("class='failcard'") == len(fs))

    print("== no retired sections ==")
    for key in ["id=\"gallery2\"", "id=\"rule\"", "id=\"resume\"", "assets2", "big2", "tabs2"]:
        print(" ", key, "->", key not in h)


if __name__ == "__main__":
    main()
