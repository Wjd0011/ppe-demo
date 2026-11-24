# -*- coding: utf-8 -*-
"""检查文档里出现的仓库内路径是否真的存在。

    python tools/check_doc_paths.py                 # 默认检查 docs/文件索引.md 与 docs/四问解答.md
    python tools/check_doc_paths.py docs/xxx.md

只检查“看起来像仓库内路径”的片段：反引号里、含 / 或 \\ 且不以 http 开头、
且能被解析成仓库内某个已存在路径的候选。带 <占位> 或 %VAR% 的跳过。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = [os.path.join(ROOT, "docs", "文件索引.md"), os.path.join(ROOT, "docs", "四问解答.md")]

# `...` 里的内容
TICK = re.compile(r"`([^`]+)`")
SKIP = ("<", ">", "%", "*", "http", " ", "\u2026", "(", ")", "|", "=")
# 仓库里存在的顶层目录/文件；候选必须以其中之一开头，否则视为普通文件名/表达式
TOPS = set(
    n for n in os.listdir(ROOT)
) | {"data.yaml", "classes.txt", "run.py", "requirements.txt", "LICENSE", "README.md"}


def candidates(text):
    for m in TICK.finditer(text):
        raw = m.group(1).strip()
        if any(s in raw for s in SKIP):
            continue
        if "/" not in raw and "\\" not in raw:
            continue                      # 裸文件名（.json / best.pt）不作为路径检查
        head = raw.replace("\\", "/").split("/")[0]
        if head not in TOPS:
            continue                      # repo/ 之类外部前缀跳过
        yield raw


def resolve(raw):
    """把 'train/images/' 'web/assets' 'tools/x.py:130-134' 之类归一化。"""
    p = raw.replace("\\", "/")
    p = p.split(":")[0]          # tools/eval_vs_gt.py:85 -> tools/eval_vs_gt.py
    p = p.split(" ")[0]
    p = p.rstrip("/")
    return os.path.join(ROOT, *p.split("/"))


def main():
    docs = sys.argv[1:] or DOCS
    missing, checked = [], 0
    for path in docs:
        if not os.path.exists(path):
            missing.append((path, "文档本身不存在"))
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        seen = set()
        for raw in candidates(text):
            if raw in seen:
                continue
            seen.add(raw)
            target = resolve(raw)
            checked += 1
            if not os.path.exists(target):
                missing.append((os.path.basename(path), raw))
    print("checked %d distinct paths in %d doc(s)" % (checked, len(docs)))
    if missing:
        print("MISSING %d:" % len(missing))
        for doc, raw in missing:
            print("  [%s] %s" % (doc, raw))
        return 1
    print("all present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
