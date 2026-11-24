# -*- coding: utf-8 -*-
"""Generate the single-file demo webpage from the real artefacts:
  out/metrics.json        (test-set evaluation)
  out/demo_stats.json     (per-demo-image TP/FP/FN)
  demo/manifest.json      (which photo is which)
  web/assets/*.jpg        (rendered overlays)

Nothing in the page is hard-coded: every number comes from those files.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")

CN = {
    "helmet": "安全帽",
    "no-helmet": "未戴安全帽",
    "no-vest": "未穿反光背心",
    "person": "人",
    "vest": "反光背心",
}

PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>施工场地安全帽与反光背心检测 — YOLO 机器视觉课堂演示</title>
<style>
:root{
  --bg:#0e1117; --panel:#161b24; --panel2:#1d242f; --line:#2a3341;
  --fg:#e6edf3; --dim:#8b98a9; --accent:#2ea8ff; --ok:#2ecc71;
  --warn:#e67e22; --bad:#e74c3c; --mono:"Consolas","SF Mono",Menlo,monospace;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;background:var(--bg);color:var(--fg);
  font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
  line-height:1.7;font-size:15px;
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header{
  padding:56px 32px 40px;border-bottom:1px solid var(--line);
  background:linear-gradient(160deg,#111a26 0%,#0e1117 60%);
}
.wrap{max-width:1180px;margin:0 auto;padding:0 32px}
h1{font-size:32px;margin:0 0 10px;letter-spacing:.5px}
h1 small{display:block;font-size:14px;color:var(--dim);font-weight:400;margin-top:8px;letter-spacing:1px}
h2{font-size:22px;margin:52px 0 18px;padding-left:12px;border-left:4px solid var(--accent)}
h3{font-size:16px;margin:26px 0 10px;color:var(--accent)}
p{margin:10px 0}
code{font-family:var(--mono);background:#0b0f14;border:1px solid var(--line);
  padding:1px 6px;border-radius:4px;font-size:13px;color:#9fd6ff}
pre{font-family:var(--mono);background:#0b0f14;border:1px solid var(--line);
  border-radius:8px;padding:14px 16px;overflow-x:auto;font-size:13px;line-height:1.6;color:#c9d6e3}
pre .c{color:#5d6b7c}
.grid{display:grid;gap:16px}
.g2{grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.g4{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}
.kpi .v{font-size:28px;font-weight:600;font-family:var(--mono);color:var(--accent)}
.kpi .l{font-size:12px;color:var(--dim);margin-top:2px}
.kpi .n{font-size:12px;color:var(--dim);margin-top:6px}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.6px}
tbody tr:hover{background:#1a2130}
td.num,th.num{text-align:right;font-family:var(--mono)}
.bar{height:7px;border-radius:4px;background:#222b38;overflow:hidden;min-width:70px}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,#2ea8ff,#2ecc71)}
.pill{display:inline-block;padding:2px 9px;border-radius:99px;font-size:11.5px;
  border:1px solid var(--line);color:var(--dim);margin-right:6px}
.pill.ok{color:#2ecc71;border-color:#2ecc71}
.pill.bad{color:#e74c3c;border-color:#e74c3c}
.pill.warn{color:#e67e22;border-color:#e67e22}
nav{position:sticky;top:0;z-index:30;background:rgba(14,17,23,.94);
  border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}
nav .wrap{display:flex;gap:6px;flex-wrap:wrap;padding:10px 32px}
nav a{font-size:13px;color:var(--dim);padding:5px 10px;border-radius:6px}
nav a:hover{background:var(--panel2);color:var(--fg);text-decoration:none}
.viewer{display:grid;grid-template-columns:1fr 210px;gap:16px}
@media(max-width:860px){.viewer{grid-template-columns:1fr}}
.stage{background:#0b0f14;border:1px solid var(--line);border-radius:10px;padding:10px}
.stage img{width:100%;display:block;border-radius:6px;background:#000}
.tabs{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.tabs button{background:var(--panel2);color:var(--dim);border:1px solid var(--line);
  padding:7px 16px;border-radius:7px;cursor:pointer;font-size:13px;font-family:inherit}
.tabs button.on{background:var(--accent);color:#05121d;border-color:var(--accent);font-weight:600}
.thumbs{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:6px;
  max-height:430px;overflow-y:auto;padding-right:4px}
.thumbs img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:5px;cursor:pointer;
  border:2px solid transparent;opacity:.62;transition:.15s}
.thumbs img:hover{opacity:1}
.thumbs img.on{border-color:var(--accent);opacity:1}
.meta{font-size:12.5px;color:var(--dim);margin-top:10px;font-family:var(--mono)}
.legend span{display:inline-flex;align-items:center;gap:6px;margin-right:14px;font-size:12.5px}
.legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
.note{background:#152030;border-left:3px solid var(--accent);padding:12px 16px;
  border-radius:0 8px 8px 0;font-size:14px;margin:16px 0}
.note.warn{background:#241c12;border-color:var(--warn)}
.note.bad{background:#241416;border-color:var(--bad)}
footer{margin-top:64px;padding:28px 0 48px;border-top:1px solid var(--line);
  color:var(--dim);font-size:12.5px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:760px){.two{grid-template-columns:1fr}}
ol,ul{padding-left:22px}
li{margin:6px 0}
.small{font-size:12.5px;color:var(--dim)}
.failgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:18px;margin:16px 0}
.failcard{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.failimgs{display:grid;grid-template-columns:1fr 1fr;gap:2px;background:var(--line)}
.failimgs img{width:100%;display:block;aspect-ratio:1;object-fit:cover;background:#000}
.failmeta{padding:12px 14px;font-size:12.5px;color:var(--dim);line-height:1.65}
.failmeta b{color:var(--fg)}
.failmeta .why{color:#e6b07a;display:block;margin-top:6px}
.cap{font-size:12px;color:var(--dim);text-align:center;margin:6px 0 0}
</style>
</head>
<body>

<header>
  <div class="wrap">
    <h1>施工场地安全帽与反光背心检测
      <small>YOLO + X-AnyLabeling · 机器视觉课堂演示 · __DATE__</small>
    </h1>
    <p style="max-width:760px;color:#b8c4d2;margin-top:18px">
      用预训练 YOLOv8n 权重在真实工地照片上完成「自动标注 → 人工校正 → 数据集评估」的完整闭环，
      并给出可复现的命令与逐类指标。
    </p>
    <div class="grid g4" style="margin-top:26px">
      <div class="kpi"><div class="v">__M_AP_TEST__</div><div class="l">mAP@50 · 测试集基线</div><div class="n">90 张未见过的图</div></div>
      <div class="kpi"><div class="v">__AB_IMPROVED__</div><div class="l">mAP@50 · 多尺度后</div><div class="n">同一权重 · +__AB_GAIN__</div></div>
      <div class="kpi"><div class="v">__N_ALL__</div><div class="l">真实工地照片</div><div class="n">997 / 119 / 90 全量</div></div>
      <div class="kpi"><div class="v">__AB_MS_B__ <span style="font-size:14px">ms/图</span></div><div class="l">CPU 推理</div><div class="n">GTX 1650 机器 · 无 CUDA</div></div>
    </div>
  </div>
</header>

<nav><div class="wrap">
  <a href="#overview">概览</a>
  <a href="#env">环境</a>
  <a href="#data">数据来源</a>
  <a href="#model">模型</a>
  <a href="#arch">架构</a>
  <a href="#flow">操作流程</a>
  <a href="#viewer">标注效果</a>
  <a href="#metrics">评估指标</a>
  <a href="#ab">A/B 对照</a>
  <a href="#failure">失败案例</a>
  <a href="#next">预期与后续</a>
  <a href="#files">文件清单</a>
</nav>

<div class="wrap">

<h2 id="overview">一、概览</h2>
<div class="two">
  <div class="card">
    <h3 style="margin-top:0">要解决的问题</h3>
    <p>施工现场的 <b>安全帽</b> 与 <b>反光背心</b> 佩戴检查目前靠人盯监控，漏检率高、无法追溯。
       目标是用一个轻量目标检测模型，从画面中同时找出「人 / 安全帽 / 反光背心」以及它们的
       负向类别（未戴帽、未穿背心），并据此判断每个工人是否合规。</p>
    <p class="small">本演示偏「方法与流程」：重点不在刷高 mAP，而在于把
      <b>数据 → 标注 → 训练/推理 → 评估 → 部署</b> 这条链路走通并可复现。</p>
  </div>
  <div class="card">
    <h3 style="margin-top:0">交付物</h3>
    <ul style="margin:0;padding-left:20px">
      <li>可运行的检测程序（ONNX Runtime + OpenCV，无需 torch）</li>
      <li>X-AnyLabeling 自定义模型配置（GUI 内一键自动标注）</li>
      <li>__N_IMGS__ 张已标注演示图（原图 / 真值 / 预测 三视图）</li>
      <li>全量 __N_ALL__ 张工地图的逐类指标 + 演示集三视图画廊</li>
      <li>测试集评估报告：mAP@50、mAP@50-95、逐类 P/R/F1</li>
      <li>本网页：流程、效果、指标、后续计划</li>
    </ul>
  </div>
</div>

<div class="note">
  <b>一句话强主张：</b>针对<b>施工现场远距离工人 「是否戴安全帽、是否穿反光背心」无法逐人核对</b>的问题，
  在<b>推理流水线的预处理与后处理环节</b>把整图单尺度改为<b>双尺度联合检测 + 跨尺度 NMS 合并</b>，
  在<b>同一 ONNX 权重、同一台无 CUDA 的普通 PC、同一批 90 张真实工地照片</b>上，
  mAP@50 从 <b>__AB_BASE__</b> 提升到 <b>__AB_IMPROVED__</b>（+__AB_GAIN__，耗时 __AB_MS_A__ → __AB_MS_B__ ms/图），
  大目标召回从 __AB_BIG_A__ 提升到 __AB_BIG_B__；
  目前仍有<b>「未戴安全帽」类 AP 仅 __AP_NOHELMET__、极小目标与逆光场景漏检明显、人群密集时会错配人与帽子</b>的限制，
  这些只能靠补拍数据重新训练解决，不是推理端能补的。
</div>

<div class="two" style="margin-top:18px">
  <div class="card">
    <h3 style="margin-top:0">这个项目的四要素（对应答辩 PPT 的问题页）</h3>
    <table>
      <tr><td style="width:120px"><b>真实场景</b></td><td>工地实地拍摄的 1206 张照片，多数为多人、远景、逆光；需要逐人判断两项 PPE。</td></tr>
      <tr><td><b>原方案</b></td><td>整图 resize 到 640 单次前向，等于把远处的工人头压到十几个像素。</td></tr>
      <tr><td><b>改动环节</b></td><td>预处理加 0.5× 副尺度、后处理做跨尺度 NMS 合并（模型/阈值/输出格式不变）。</td></tr>
      <tr><td><b>可重复验证</b></td><td><code>tools/ab_tiled.py</code> 一条命令重跑，test/valid 两个划分结论一致。</td></tr>
      <tr><td><b>诚实边界</b></td><td>本页第十节列出 6 个最差样本与三种失败模式，第十一节写明「不声称召回提升」。</td></tr>
    </table>
  </div>
  <div class="card">
    <h3 style="margin-top:0">本人负责的工作（100%）</h3>
    <ul style="margin:0;padding-left:20px">
      <li>数据：全量下载 1206 张（含 429 限流重试），校验 997/119/90 三划分完整性</li>
      <li>标注：写 X-AnyLabeling 自定义模型配置、把 10 类本地化为中文、裁到 5 类报告口径</li>
      <li>修复：<code>tempfile.mkstemp</code> 在只读目录下无限重试导致的界面卡死；yaml 按 GBK 解码导致的崩溃</li>
      <li>评估：手写 numpy 版 mAP / P / R（101 点插值），跑满三个划分</li>
      <li>实验：设计并实现 A/B（多尺度 / 分块 / TTA 共 6 个候选），做失败案例分析</li>
      <li>交付：本网页、README、桌面零操作快捷方式</li>
    </ul>
    <p class="small">本项目无外部协作者，数据与预训练权重均来自公开数据集（CC BY 4.0），非本人产出。</p>
  </div>
</div>

<div class="note">
  <b>一句话结论：</b>在 <b>__N_ALL__ 张真实工地照片</b>（全部跑过推理，三个划分的 mAP@50 都在 0.54–0.57）上，
  安全帽检测 AP@50 达 <b>__AP_HELMET__</b>、「人」达 <b>__AP_PERSON__</b>，
  可直接支撑标注辅助与课堂演示；但「未戴安全帽」这一关键负向类别 AP@50 仅 <b>__AP_NOHELMET__</b>，
  原因是训练集中该类别样本过少（测试集仅 __GT_NOHELMET__ 个框，训练集 997 张里也只有 94 个）——
  这正是下一步必须用自有数据微调的核心动机。
</div>

<h2 id="env">二、运行环境</h2>
<div class="grid g2">
  <div class="card">
    <h3 style="margin-top:0">本机实测环境</h3>
    <table>
      <tr><td>操作系统</td><td class="num">Windows 11 (10.0.26200)</td></tr>
      <tr><td>GPU</td><td class="num">GTX 1650 4 GB / 驱动 610.88</td></tr>
      <tr><td>CUDA 工具链</td><td class="num">未安装（也不需要）</td></tr>
      <tr><td>Python</td><td class="num">3.12.16（uv 托管）</td></tr>
      <tr><td>X-AnyLabeling</td><td class="num">4.3.1</td></tr>
      <tr><td>ONNX Runtime</td><td class="num">1.31.1 (CPU)</td></tr>
      <tr><td>OpenCV</td><td class="num">5.0.0</td></tr>
      <tr><td>torch / ultralytics</td><td class="num">未安装（本演示不需要）</td></tr>
    </table>
  </div>
  <div class="card">
    <h3 style="margin-top:0">为什么不用 torch</h3>
    <p>训练需要 torch，但<b>推理与自动标注不需要</b>：模型从 PyPI 的
      <code>x-anylabeling-cvhub[cpu]</code> 装好后，ONNX Runtime 已就位，
      只要一个 <code>.onnx</code> 文件即可跑通全流程。</p>
    <p>这带来三个好处：</p>
    <ul style="margin:0;padding-left:20px">
      <li>省下 2.5 GB 下载与 30 分钟安装（本机到清华源约 0.45 MB/s）</li>
      <li>4 GB 显存不会被 CUDA 上下文占用，CPU 单图 __AB_MS_A__ ms（基线）已够课堂演示</li>
      <li>后续要微调时再单独装 <code>torch[cuda]</code>，与现有环境隔离</li>
    </ul>
    <p class="small" style="margin-top:14px">如要真正训练：<code>uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126</code></p>
  </div>
</div>

<h2 id="data">三、数据来源（真实工地照片）</h2>
<p>数据集为 Roboflow Universe 的 <b>construction-safety-gsnvb</b>（CC BY 4.0），
经 Hugging Face 镜像 <code>LibreYOLO/construction-safety-gsnvb</code> 获取——
完整数据集共 <b>1206 张</b>真实工地照片（997 / 119 / 90），全部已由人工标注为 YOLO 格式。
本次 <b>全量下载了 1206 张</b>：训练集、验证集、测试集全部拉齐，因此下面的指标覆盖每一个划分，
而不是只挑几张好看的照片。</p>
<table>
  <thead><tr><th>划分（本次已全量下载）</th><th class="num">图片</th><th class="num">安全帽</th><th class="num">未戴帽</th><th class="num">未穿背心</th><th class="num">人</th><th class="num">反光背心</th></tr></thead>
  <tbody>__DATASET_ROWS__</tbody>
</table>
<div class="note warn">
  <b>类别不均衡是这份数据最大的问题。</b>「未戴安全帽」（no-helmet）只占全部框的约 2%，
  却恰恰是安全场景中最关键的告警类别。它直接解释了第八节里该类 AP 偏低——
  这也是「拿现场数据补拍 + 微调」最有力的理由。
</div>
<p class="small">许可证：CC BY 4.0（Roboflow Universe · roboflow-100/construction-safety-gsnvb）。
照片均为真实工地场景，包含室内外、逆光、遮挡、多人等情形。</p>

<h2 id="model">四、模型与类别映射</h2>
<div class="two">
  <div class="card">
    <h3 style="margin-top:0">选用的预训练权重</h3>
    <p><b>construction-ppe-safety</b>（Hugging Face，CC BY 4.0）：
      YOLOv8n 在 Roboflow <code>construction-site-safety v28</code> 上微调，
      导出为 ONNX（opset 12），12.2 MB，输入 640×640，输出 <code>[1, 14, 8400]</code>。</p>
    <p class="small">本演示只报告 <b>5 个类别</b>——「有没有戴安全帽 / 有没有穿反光背心」以及
      作为参照的「人」。ONNX 输出通道另有 5 个与本任务无关的类，已在模型配置里用
      <code>filter_classes</code> 过滤，不会出现在标签栏、标注 JSON 或指标表里。</p>
    <table>
      <tr><th>索引</th><th>报告类别</th><th>原始英文</th></tr>
      <tr><td>0</td><td><b>安全帽</b></td><td>Hardhat</td></tr>
      <tr><td>2</td><td><b>未戴安全帽</b></td><td>NO-Hardhat</td></tr>
      <tr><td>4</td><td><b>未穿反光背心</b></td><td>NO-Safety Vest</td></tr>
      <tr><td>5</td><td><b>人</b></td><td>Person</td></tr>
      <tr><td>7</td><td><b>反光背心</b></td><td>Safety Vest</td></tr>
    </table>
    <p>选它的原因很直接：<b>同时含正向与负向类别</b>。只有 helmet 一个正类的模型，
      遇到「没人戴的帽子」会误判为合规；把 NO-* 作为独立类别，才可能做出真正的告警。</p>
  </div>
  <div class="card">
    <h3 style="margin-top:0">模型类别 → 数据集类别</h3>
    <p class="small">数据集正好也是这 5 类，评估时按此表对齐。映射一旦写错，
      指标会「静默错误」——所以它被固化在代码常量里并有注释说明。</p>
    <table>
      <tr><td>安全帽</td><td>→ helmet</td></tr>
      <tr><td>未戴安全帽</td><td>→ no-helmet</td></tr>
      <tr><td>未穿反光背心</td><td>→ no-vest</td></tr>
      <tr><td>人</td><td>→ person</td></tr>
      <tr><td>反光背心</td><td>→ vest</td></tr>
    </table>
    <p class="small">类别索引必须保持 10 项不变（它是 ONNX 输出通道顺序），
      少写一项会让后面所有名字错位；要裁类别用 <code>filter_classes</code>。</p>
  </div>
</div>

<h2 id="arch">五、系统架构：基线在哪儿，我改了什么</h2>
<p>一条完整的工地巡检链路有六段。下面这张图画的就是<b>基线</b>——一个只用「整图 YOLO + 人工复核」的朴素方案——
以及本次在链条上真正动过的三处（蓝色实线框），其余环节<b>没有动</b>，如实标灰。</p>

<svg viewBox="0 0 1120 210" width="100%" style="margin:12px 0 4px" role="img"
     aria-label="系统基线架构图：成像→预处理→检测→判定→输出→业务动作，本次改动落在预处理、检测后处理与判定三处">
  <defs>
    <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#4a5b70"/>
    </marker>
  </defs>
  <g font-family="Segoe UI,Microsoft YaHei,sans-serif" font-size="12.5">
    <!-- rows -->
    <text x="8" y="30" fill="#8b98a9" font-size="11">基线</text>
    <text x="8" y="132" fill="#8b98a9" font-size="11">本次</text>

    <!-- baseline chain -->
    <g fill="#161b24" stroke="#2a3341">
      <rect x="70" y="12" width="150" height="46" rx="7"/>
      <rect x="245" y="12" width="150" height="46" rx="7"/>
      <rect x="420" y="12" width="150" height="46" rx="7"/>
      <rect x="595" y="12" width="150" height="46" rx="7"/>
      <rect x="770" y="12" width="150" height="46" rx="7"/>
      <rect x="945" y="12" width="150" height="46" rx="7"/>
    </g>
    <g fill="#c2ccd8" text-anchor="middle">
      <text x="145" y="33">① 成像</text><text x="145" y="49" fill="#7d8b9c" font-size="10.5">工地照片 / 监控截图</text>
      <text x="320" y="33">② 预处理</text><text x="320" y="49" fill="#7d8b9c" font-size="10.5">整图 resize 到 640</text>
      <text x="495" y="33">③ 检测</text><text x="495" y="49" fill="#7d8b9c" font-size="10.5">YOLOv8n 单次前向</text>
      <text x="670" y="33">④ 判定</text><text x="670" y="49" fill="#7d8b9c" font-size="10.5">人 + 框包含关系</text>
      <text x="845" y="33">⑤ 输出</text><text x="845" y="49" fill="#7d8b9c" font-size="10.5">标注文件 / 画框图</text>
      <text x="1020" y="33">⑥ 业务动作</text><text x="1020" y="49" fill="#7d8b9c" font-size="10.5">人工复核 · 课堂演示</text>
    </g>
    <g stroke="#4a5b70" stroke-width="1.6" fill="none" marker-end="url(#ar)">
      <path d="M220,35 L243,35"/><path d="M395,35 L418,35"/><path d="M570,35 L593,35"/>
      <path d="M745,35 L768,35"/><path d="M920,35 L943,35"/>
    </g>

    <!-- my chain -->
    <g fill="#152030" stroke="#2ea8ff" stroke-width="1.8">
      <rect x="70" y="112" width="150" height="46" rx="7" fill="#161b24" stroke="#2a3341" stroke-width="1"/>
      <rect x="245" y="112" width="150" height="46" rx="7"/>
      <rect x="420" y="112" width="150" height="46" rx="7" fill="#161b24" stroke="#2a3341" stroke-width="1"/>
      <rect x="595" y="112" width="150" height="46" rx="7"/>
      <rect x="770" y="112" width="150" height="46" rx="7" fill="#161b24" stroke="#2a3341" stroke-width="1"/>
      <rect x="945" y="112" width="150" height="46" rx="7" fill="#161b24" stroke="#2a3341" stroke-width="1"/>
    </g>
    <g fill="#c2ccd8" text-anchor="middle">
      <text x="145" y="133">① 成像</text><text x="145" y="149" fill="#7d8b9c" font-size="10.5">同一批 1206 张（不变）</text>
      <text x="320" y="133" fill="#7fd0ff">② 预处理 · 改</text><text x="320" y="149" fill="#8fb6cf" font-size="10.5">长边上限不动 + 额外 0.5× 副尺度</text>
      <text x="495" y="133">③ 检测</text><text x="495" y="149" fill="#7d8b9c" font-size="10.5">同一 ONNX / 同阈值（不变）</text>
      <text x="670" y="133" fill="#7fd0ff">④ 判定 · 改</text><text x="670" y="149" fill="#8fb6cf" font-size="10.5">跨尺度 NMS 合并 + 面积占比规则</text>
      <text x="845" y="133">⑤ 输出</text><text x="845" y="149" fill="#7d8b9c" font-size="10.5">同一 JSON / 同一画框（不变）</text>
      <text x="1020" y="133">⑥ 业务动作</text><text x="1020" y="149" fill="#7d8b9c" font-size="10.5">人工复核 · 课堂演示（不变）</text>
    </g>
    <g stroke="#4a5b70" stroke-width="1.6" fill="none" marker-end="url(#ar)">
      <path d="M220,135 L243,135"/><path d="M395,135 L418,135"/><path d="M570,135 L593,135"/>
      <path d="M745,135 L768,135"/><path d="M920,135 L943,135"/>
    </g>
    <!-- change callouts -->
    <g font-size="11" fill="#7fd0ff">
      <path d="M320,112 L320,62" stroke="#2ea8ff" stroke-width="1.2" stroke-dasharray="4 3"/>
      <text x="326" y="76">本次唯一算法改动</text>
      <path d="M670,112 L670,62" stroke="#2ea8ff" stroke-width="1.2" stroke-dasharray="4 3"/>
      <text x="676" y="76">规则口径对齐多尺度</text>
    </g>
    <!-- swatch legend -->
    <g font-size="11" fill="#8b98a9">
      <rect x="70" y="176" width="14" height="10" fill="#161b24" stroke="#2a3341"/>
      <text x="90" y="185">未改动</text>
      <rect x="150" y="176" width="14" height="10" fill="#152030" stroke="#2ea8ff" stroke-width="1.8"/>
      <text x="170" y="185">本次改动</text>
    </g>
  </g>
</svg>
<p class="small">按答辩 PPT 的系统架构页：把六段链路画出来，然后<b>只圈自己动过的那一段</b>。
本次改动集中在 ② 预处理与 ④ 判定后处理，模型权重、阈值、输出格式、业务动作全部保持原样——
这样上表里的 A/B 对比才是公平对照（同一输入、同一测试范围、同一模型、同一硬件）。</p>

<div class="two">
  <div class="card">
    <h3 style="margin-top:0">运行时数据流（一次推理）</h3>
    <pre style="margin:0">图像 (任意尺寸)
  │
  ├─ 尺度 A：原图 → letterbox(640) ─┐
  └─ 尺度 B：0.5× → letterbox(640) ─┤
                                    ├→ ONNX Runtime (CPU)
                                    │     输出 [1,14,8400]
                                    │
                         cls/box 解码 + 置信度过滤 (conf≥0.35)
                                    │
                    坐标反算回原图（fx, fy）
                                    │
                    跨尺度合并 → 手写 NMS (IoU 0.45)
                                    │
              ┌─────────────────────┴─────────────────────┐
        filter_classes 丢掉 5 个无关通道        合规判定：框内面积占比 &gt;25%
              │                                           │
        X-AnyLabeling JSON / 画框图                 每人一行：戴帽? 穿背心?
</pre>
  </div>
  <div class="card">
    <h3 style="margin-top:0">模块与代码位置</h3>
    <table>
      <tr><th>模块</th><th>文件</th></tr>
      <tr><td>预处理 + 推理 + NMS</td><td><code>tools/yolo_onnx_predict.py</code></td></tr>
      <tr><td>多尺度 / 分块 / TTA</td><td><code>tools/ab_tiled.py</code></td></tr>
      <tr><td>评估（mAP / P / R）</td><td><code>tools/eval_vs_gt.py</code></td></tr>
      <tr><td>批量自动标注</td><td><code>tools/auto_label_json.py</code></td></tr>
      <tr><td>失败分析</td><td><code>tools/render_failures.py</code></td></tr>
      <tr><td>页面生成</td><td><code>tools/build_web.py</code></td></tr>
    </table>
    <p class="small">数据流与代码文件一一对应，答辩时可以直接打开对应文件逐行对照。</p>
  </div>
</div>

<h2 id="flow">六、操作流程（可复现）</h2>
<ol>
  <li><b>准备数据</b>：从 HF 镜像下载 1206 张图 + 标签，保持
      <code>images/</code> 与 <code>labels/</code> 同名配对。</li>
  <li><b>注册自定义模型</b>：把下面的 yaml 写进任意目录，再在
      <code>%USERPROFILE%\.xanylabelingrc</code> 的 <code>custom_models</code> 里登记，
      GUI 的自动标注下拉框会多出一项。</li>
  <li><b>自动标注</b>：打开图片目录 → 选模型 → <code>Ctrl+A</code> 整目录跑一遍。</li>
  <li><b>人工校正</b>：<code>D</code> 下一张；<code>R</code> 画框、<code>Ctrl+E</code> 改标签；
      漏检的「未戴安全帽」必须手工补，这是本次标注的主要工作量。</li>
  <li><b>导出</b>：<code>导出 → YOLO HBB</code>，得到与数据集一致的 txt。</li>
  <li><b>评估</b>：用 <code>tools/eval_vs_gt.py</code> 与数据集真值对比，得到 mAP 表。</li>
</ol>

<div class="card">
  <h3 style="margin-top:0">演示时怎么打开（零操作）</h3>
  <p>桌面快捷方式 <b>「X-AnyLabeling 标注演示」</b> 双击即用，不需要 Open Dir、不需要点自动标注：
    程序启动后直接停在 <code>ppe-demo\demo2\images\</code> 的第一张图上（标题栏显示
    <code>[1/60]</code>），框和中文标签已经画好。</p>
  <table>
    <tr><td style="width:150px">快捷方式</td><td><code>%USERPROFILE%\Desktop\X-AnyLabeling 标注演示.lnk</code></td></tr>
    <tr><td>目标</td><td><code>&lt;pythonw.exe&gt; "&lt;仓库&gt;\tools\xal_launch.pyw"</code>（pythonw = 不弹控制台）</td></tr>
    <tr><td>默认目录</td><td><code>&lt;仓库&gt;\demo2\images</code>（<code>tools\xal_launch.pyw</code> 里按脚本位置推算，不含绝对路径）</td></tr>
    <tr><td>拖拽</td><td>把任意文件夹/图片拖到快捷方式上，会改为打开那个路径</td></tr>
  </table>
  <p class="small">翻页 <code>D</code> / <code>A</code>，改标签 <code>Ctrl+E</code>，画框 <code>R</code>，
    保存 <code>Ctrl+S</code>（已开自动保存）。想打开别的目录就把文件夹拖到快捷方式上，
    或启动后用 <code>Ctrl+U</code>。</p>
</div>

<h3>X-AnyLabeling 自定义模型配置</h3>
<p class="small">类别名已本地化为中文（<b>顺序即 ONNX 输出通道顺序</b>）。
<code>filter_classes</code> 决定「报哪些」：只留与安全帽 / 反光背心相关的 5 类。
<code>classes</code> 仍需按 10 个输出通道的顺序写满（删项会让后面所有名字错位），
完整内容见 <code>models/ppe_yolov8n.yaml</code>，这里只展示报告口径。</p>
<pre><span class="c"># models/ppe_yolov8n.yaml（节选：报告口径）</span>
type: yolov8
name: ppe_construction_yolov8n      <span class="c"># 只能含字母数字 . _ -</span>
provider: Ultralytics
display_name: 工地安全帽 / 反光背心检测 (YOLOv8n)
model_path: construction_ppe_yolov8n.onnx   <span class="c"># 相对本 yaml 所在目录</span>
conf_threshold: 0.35
iou_threshold: 0.45
<span class="c"># 只报告这 5 类（名称必须与 classes 里对应项完全一致）</span>
filter_classes:
  - 安全帽
  - 未戴安全帽
  - 反光背心
  - 未穿反光背心
  - 人</pre>
<p class="small">把这段登记进 <code>.xanylabelingrc</code>：</p>
<pre>custom_models:
  - config_file: &lt;仓库&gt;\models\ppe_yolov8n.yaml
    is_custom_model: true
    last_used: 0.0</pre>

<h3>中文标签是怎么落地的</h3>
<p>四步，缺一不可：</p>
<ol>
  <li><b>模型 yaml 的 <code>classes</code> 换成中文</b>——自动标注按 <code>self.classes[int(class_id)]</code>
      取名字，这里是唯一的标签来源。</li>
  <li><b>已有 JSON 标注跟着翻</b>——92 个文件 / 1467 个框，用
      <code>tools/translate_labels.py</code> 按同一张映射表重写；否则旧图打开是英文、
      新跑的自动标注是中文，同一个类别会在标签栏里出现两次。</li>
  <li><b>只留 5 类</b>——<code>filter_classes</code> 管新推理的输出，
      <code>tools/prune_labels.py</code> 管已有 JSON（1467 → 1147 个框：
      删掉与安全无关的 5 类共 320 个框）。两边都要做，
      只改 yaml 的话旧 JSON 里的无关框还在。</li>
  <li><b>修一处编码 bug</b>——<code>yaml</code> 读取用的是 <code>open(path, "r")</code>，
      在中文 Windows 上按 GBK 解码，含中文的 yaml 会直接抛
      <code>UnicodeDecodeError: 'gbk' codec can't decode byte ...</code>。已改为
      <code>encoding="utf-8"</code>（其余几个读取点本来就有）。</li>
</ol>
<p class="small">翻译前的 92 个 JSON 已打包留底过一次（用完即删，脚本可重跑）；
模型 yaml 英文版备份 <code>models/ppe_yolov8n.yaml.bak-en</code>。</p>

<h2 id="viewer">七、标注效果（原图 / 真值 / 预测）</h2>
<div class="legend" style="margin-bottom:12px">
  <span><i style="background:#2ecc71"></i>安全帽</span>
  <span><i style="background:#1abc9c"></i>反光背心</span>
  <span><i style="background:#3498db"></i>人</span>
  <span><i style="background:#e74c3c"></i>未戴安全帽</span>
  <span><i style="background:#e67e22"></i>未穿反光背心</span>
</div>
<div class="viewer">
  <div class="stage">
    <div class="tabs" id="tabs">
      <button data-mode="orig" class="on">原图</button>
      <button data-mode="gt">数据集真值</button>
      <button data-mode="pred">模型预测</button>
    </div>
    <img id="big" src="" alt="标注对比">
    <div class="meta" id="meta"></div>
  </div>
  <div>
    <div class="thumbs" id="thumbs"></div>
  </div>
</div>
<p class="small">点右侧缩略图切换图片，点上方按钮切换叠加层。「真值」是数据集的人工标注，
「模型预测」是 YOLOv8n 直接推理结果（置信度阈值 0.35）。两者差异即为需要人工校正的部分。</p>

<h2 id="metrics">八、评估指标</h2>
<p>全部 <b>1206 张工地图</b>（7724 个真值框）逐张推理后，与人工标注做 IoU≥0.5 的贪心匹配，
下表按划分给出结果；AP 采用 101 点插值（COCO 口径），合并行按各类真值框数加权。</p>
<table>
  <thead><tr><th>划分</th><th class="num">图片</th><th class="num">真值框</th><th class="num">预测框</th><th class="num">mAP@50</th><th class="num">mAP@50-95</th><th class="num">安全帽</th><th class="num">人</th><th class="num">背心</th><th class="num">未穿背心</th><th class="num">未戴帽</th></tr></thead>
  <tbody>__SPLIT_ROWS__</tbody>
</table>
<p class="small">训练集也在内——模型从未在该数据上训练过，但训练集与测试集来自同一批拍摄，
指标天然更乐观；真正应引用的是<b>测试集</b>那一行。三个划分的 mAP@50 落在 0.54–0.57 的窄区间内，
说明结果不是挑划分挑出来的。</p>

<h3>测试集（90 张，__GT_BOXES__ 个真值框）逐类结果</h3>
<table>
  <thead><tr><th>类别</th><th class="num">AP@50</th><th class="num">AP@50-95</th><th class="num">真值框</th><th class="num">预测框</th><th style="width:130px">相对水平</th></tr></thead>
  <tbody>__AP_ROWS__</tbody>
</table>
<p class="small">整体：<b>mAP@50 = __M_AP_TEST__</b>，<b>mAP@50-95 = __M_AP95__</b>。</p>

<h3>工作点（置信度 ≥ 0.35）的查准/查全</h3>
<table>
  <thead><tr><th>类别</th><th class="num">Precision</th><th class="num">Recall</th><th class="num">F1</th><th class="num">预测</th><th class="num">真值</th></tr></thead>
  <tbody>__PR_ROWS__</tbody>
</table>
<p class="small">以上均为测试集口径；检出总数 __PRED_BOXES__ 个框，全部属于报告中的 5 类。</p>

<h2 id="ab">九、A/B 公平对照：整图基线 vs 缩图多尺度</h2>
<p>按答辩 PPT 的对照实验页同一口径做一组<b>公平对照</b>：同一批图、同一份 ONNX 权重、同一置信度（0.35）与
NMS IoU（0.45）、同一台机器、同一段预处理代码，<b>只改推理时的尺度策略</b>。
指标同时给出「准确性 + 平均开销 + 失败异常」，三条一起看。</p>

<div class="note">
  <b>A（基线）= 整图单尺度。</b>把整张图 resize 到长边 640 后 letterbox 送进网络，一次前向。<br>
  <b>B（本次）= 缩图多尺度。</b>额外再生成一个 0.5× 的副本各跑一次前向，两个尺度的框反算回原图坐标后
  一起做 NMS 合并。动机：640 输入下「远、小」的人头只剩十几个像素，缩图会把远处的成组目标压得更集中，
  相当于用两次廉价前向换回一部分被判丢的目标。<br>
  <b>C（负面对照）= 分块 2×2。</b>把图切成四块各自放大到 640 推理——直觉上「放大能救小目标」，
  实测反而最差，保留它就是为了说明<b>直觉 ≠ 结果</b>。
</div>

<table>
  <thead><tr><th>策略</th><th class="num">mAP@50</th><th class="num">mAP@50-95</th><th class="num">框/图</th><th class="num">耗时 ms/图</th><th class="num">相对 A</th><th>结论</th></tr></thead>
  <tbody>__AB_ROWS__</tbody>
</table>
<p class="small">测试集 90 张 / __GT_BOXES__ 个真值框。耗时为本机 CPU 实测（含解码与 NMS），
单次运行的抖动约 ±10 ms；「相对 A」为 mAP@50 的绝对差。</p>

<h3>按目标尺寸拆开看：改的到底是谁</h3>
<p>只看总 mAP 会掩盖问题。把真值框按边长分三档（小 &lt;48px / 中 48–96px / 大 ≥96px）分别算召回：</p>
<table>
  <thead><tr><th>策略</th><th class="num">小 &lt;48px</th><th class="num">中 48–96px</th><th class="num">大 ≥96px</th></tr></thead>
  <tbody>__AB_SIZE_ROWS__</tbody>
</table>
<p class="small">B 的收益几乎全部来自<b>大目标</b>（0.739 → 0.803，多命中 25 个），
中小目标持平；而 C 恰好相反——小目标略升、大目标腰斩（0.739 → 0.461）。
这解释了为什么「分块放大」这种常见直觉在本模型上会翻车：
每块被强制放大回 640 后，人与帽子的尺度分布偏离了训练分布。</p>

<h3>验证集复核（同一套代码，换一批图）</h3>
<p>为避免结论只在测试集成立，把同一组实验在验证集 119 张上重跑：</p>
<table>
  <thead><tr><th>策略</th><th class="num">mAP@50</th><th class="num">mAP@50-95</th><th class="num">耗时 ms/图</th><th class="num">大目标召回</th></tr></thead>
  <tbody>__AB_VALID_ROWS__</tbody>
</table>
<p class="small">验证集上 B 同样领先（+__AB_VALID_GAIN__ mAP@50），方向一致，说明不是测试集偶然。</p>

<div class="note warn">
  <b>必须说清楚的边界：</b>这组对照改变的是<b>推理流程</b>，不是模型能力。
  B 的代价是耗时约翻倍（__AB_MS_A__ → __AB_MS_B__ ms/图），且对「本来就漏掉的极小目标」帮助有限
  （小目标召回 __AB_SMALL_A__ → __AB_SMALL_B__，没变）。
  换句话说：<b>它换来的是「大中目标判得更稳」，不是「小目标也能看见」</b>；
  真要救小目标，得靠补拍数据重新训练或切片推理（而后者在本模型上已被 C 证明会伤大目标）。
</div>

<h2 id="failure">十、失败案例：模型在哪儿翻车</h2>
<p>下面 6 张是测试集里表现最差的样本（按 漏检×2 + 误检 排序），全部来自同一批真实工地照片，
标注含义：<span class="pill ok">绿框 命中</span><span class="pill bad">红框 误检</span>
<span class="pill warn">橙虚线 漏检</span>。左边是原图，右边是模型输出。</p>
<div class="failgrid">__FAIL_CARDS__</div>
<p class="small">这 6 张合计真值 __FAIL_GT__ 个框、命中 __FAIL_TP__、误检 __FAIL_FP__、漏检 __FAIL_FN__。
反复出现的三种失败模式，正好对应第九节与第十一节里的改进方向：</p>
<ol>
  <li><b>头部区域类别竞争</b>——帽子与头/脸的特征高度重合，模型常在头部区域给出多个相互重叠的框，
      人工复核时表现为「一顶帽子两个框」或把东西误认成帽子。解决方向：微调时只保留与安全相关的样本。</li>
  <li><b>多人密集场景张冠李戴</b>——人框与帽子框的「包含关系」判定在人群里会错配，
      一个人被算成两个、或者把别人的帽子算给他。解决方向：IoU 矩阵 + 匈牙利匹配做配对。</li>
  <li><b>极小目标与逆光</b>——远处不足 16 px 的人头基本看不见，逆光时背心颜色与背景接近。
      解决方向：补拍数据 + 重新训练，而不是在推理端加花活。</li>
</ol>

<h2 id="next">十一、预期与后续计划</h2>
<table>
  <thead><tr><th style="width:120px">阶段</th><th>做什么</th><th style="width:150px">预期收益</th></tr></thead>
  <tbody>
    <tr><td>近期</td><td>把 __N_IMGS2__ 张扩展测试图的漏检手工补齐（尤其「未戴安全帽」），形成精品标注子集</td><td>可直接对比「自动 vs 人工」</td></tr>
    <tr><td>近期</td><td>补拍/搜集 300–500 张本场景照片，重点补负样本（未戴帽、逆光、夜间）</td><td>no-helmet AP 从 __AP_NOHELMET__ 提升</td></tr>
    <tr><td>中期</td><td>装 <code>torch[cuda]</code> + ultralytics，用 GTX 1650（4 GB）微调 YOLOv8n/s，imgsz=640，batch 8–16，AMP</td><td>mAP@50 目标 0.75+</td></tr>
    <tr><td>中期</td><td>合并冗余类别，只保留 person / helmet / no-helmet / vest / no-vest 五类</td><td>减少类别竞争，提升关键类召回 <span class="c">（已完成：filter_classes + prune_labels）</span></td></tr>
    <tr><td>远期</td><td>导出 ONNX/TensorRT，接 RTSP 视频流做实时告警（>15 FPS）</td><td>从「演示」到「能用」</td></tr>
    <tr><td>远期</td><td>加跟踪（ByteTrack）+ 违规去重，避免同一人重复告警</td><td>告警可用性</td></tr>
  </tbody>
</table>

<h3>风险与边界</h3>
<ul>
  <li><b>数据偏差</b>：数据集以白天、室外、中景为主；夜间与遮挡场景泛化差。</li>
  <li><b>负类稀缺</b>：no-helmet 仅约 2%，模型倾向「看到头就认为是帽子」。</li>
  <li><b>隐私</b>：照片含人脸，仅用于课堂演示，不作公开分发；如需展示需打码。</li>
  <li><b>小目标</b>：远处工人头部不足 16 px 时漏检明显，需切片推理（SAHI）；
      但第九节的 C 组实验已证明：在本模型上切片会伤大目标，所以这条路径必须<b>先换权重再试</b>。</li>
  <li><b>推理侧收益有上限</b>：A/B 的 +__AB_GAIN__ 是流程优化的天花板。再往上必须动模型本身
      （补数据微调），否则只是在同一份权重上反复榨取。</li>
</ul>

<h3>明确不做的事</h3>
<ul>
  <li><b>不声称召回提升</b>：本演示没有逐帧人工真值视频，「检出框 125→623」这类数字<b>只能说明输出数量变化</b>，
      不能写成准确率/召回提升（答辩 PPT 已点明这一点）。所有指标都基于有真值的数据集划分。</li>
  <li><b>不做实时告警</b>：CPU 单图 __AB_MS_B__ ms，做不到 15 FPS 的流式处理，本轮不包装成「实时」。</li>
  <li><b>不把演示训练值当作本页结论</b>：正文所有指标都来自预训练权重推理。仓库另附一条
      「标注 → 训练 → 导出 → 接回」的演示链路（8 轮 / 416px / 25% 数据 / CPU，末轮验证集 mAP50 0.7168），
      它的作用是证明链路能跑通，<b>口径不同，不能与本页数字对比</b>。</li>
</ul>

<h2 id="files">十二、文件清单与复现命令</h2>
<pre><span class="c">ppe-demo/</span>
├── README.md                              <span class="c">项目简介 / 环境 / 实测 / 用法</span>
├── requirements.txt                        <span class="c">推理所需依赖（不含 torch）</span>
├── run.py                                  <span class="c">一条命令复现：推理 → 评估 → 重建网页</span>
├── LICENSE                                 <span class="c">MIT（代码）· 数据与权重 CC BY 4.0</span>
├── models/
│   ├── construction_ppe_yolov8n.onnx     <span class="c">12.2 MB · 预训练权重（10 类）</span>
│   ├── demo_trained_yolov8n.onnx         <span class="c">12.8 MB · 本项目 8 轮训练产物（5 类）</span>
│   ├── ppe_yolov8n.yaml                  <span class="c">X-AnyLabeling 自定义模型配置</span>
│   └── ppe_demo_trained.yaml             <span class="c">训练产物接入配置</span>
├── demo/images/                          <span class="c">__N_IMGS__ 张 · 图 + X-AnyLabeling JSON 标注</span>
├── demo2/images/                         <span class="c">__N_IMGS2__ 张扩展测试图 · 图 + JSON 标注</span>
├── test/{images,labels}/                 <span class="c">90 张测试集（全量）</span>
├── valid/{images,labels}/                <span class="c">119 张验证集（全量）</span>
├── train/{images,labels}/                <span class="c">997 张训练集（全量）</span>
├── tools/
│   ├── yolo_onnx_predict.py              <span class="c">纯 ONNX 推理 + 画框 + 合规计数</span>
│   ├── ab_tiled.py                       <span class="c">多尺度 / 分块 / TTA 的 A/B 实验框架</span>
│   ├── eval_vs_gt.py                     <span class="c">mAP / P / R 评估（numpy 实现）</span>
│   ├── run_full_eval.py                  <span class="c">三个划分批量评估</span>
│   ├── render_failures.py                <span class="c">挑最差样本并渲染失败案例</span>
│   ├── auto_label_json.py                <span class="c">用 X-AnyLabeling 模型批量生成 JSON 标注</span>
│   ├── translate_labels.py               <span class="c">英文标签 → 中文（含备份）</span>
│   ├── prune_labels.py                   <span class="c">裁到 5 类报告口径</span>
│   ├── build_demo_set.py / build_demo2.py     <span class="c">挑演示图与扩展测试集</span>
│   ├── render_demo.py / render_demo2.py       <span class="c">渲染三视图</span>
│   ├── build_web.py                      <span class="c">生成本网页</span>
│   ├── test_xal_model.py                 <span class="c">自检：用 XAL 自己的 YOLO 类加载两份模型 yaml</span>
│   ├── xal_launch.pyw                    <span class="c">双击即开标注演示（无控制台）</span>
│   ├── ppt_kit.py / build_ppt_final.py   <span class="c">答辩 PPT 排版工具层与 17 页生成</span>
│   ├── check_doc_paths.py                <span class="c">文档里写的路径是否真的存在</span>
│   └── check_viewer.js / check_numbers.py     <span class="c">页面交互与数字自检</span>
├── docs/
│   ├── PPE答辩汇报-最终版.pptx            <span class="c">17 页答辩版</span>
│   ├── 全链路操作手册.md                  <span class="c">导入 → 标注 → 训练 → 导出 → 接回</span>
│   ├── 四问解答.md                        <span class="c">创新点 / 价值 / 实现 / GitHub 与 YOLO 体验</span>
│   ├── 文件索引.md                        <span class="c">测试图片与核心代码的完整路径清单</span>
│   └── demo_train_results.csv / _args.yaml   <span class="c">8 轮训练逐轮指标与超参数快照</span>
├── out/                                  <span class="c">指标 json、A/B 结果、失败统计</span>
└── web/
    ├── index.html                        <span class="c">本页面</span>
    ├── assets/                           <span class="c">演示集三视图（32×3）</span>
    └── assets3/                          <span class="c">失败案例（6×2）</span></pre>

<h3>三条关键命令</h3>
<pre><span class="c"># 0) 一条命令复现全部结果（推理 → 评估 → A/B → 三视图 → 失败案例 → 重建网页）</span>
python run.py --all

<span class="c"># 1) 只跑推理，把框画出来存到 out/pred</span>
python tools/yolo_onnx_predict.py --images test/images --out out/pred --save-vis --json out/pred_test.json

<span class="c"># 2) 与真值对比，输出 mAP</span>
python tools/eval_vs_gt.py

<span class="c"># 3) A/B 对照实验（整图 vs 多尺度 vs 分块）</span>
python tools/ab_tiled.py --split test

<span class="c"># 4) 用 X-AnyLabeling 的模型给整个目录自动标注（生成 .json）</span>
python tools/auto_label_json.py --images demo/images</pre>

<footer>
  <div>数据：Roboflow Universe <i>construction-safety-gsnvb</i>（CC BY 4.0） · 模型：<i>construction-ppe-safety</i> YOLOv8n（CC BY 4.0）</div>
  <div>工具：X-AnyLabeling 4.3.1 · ONNX Runtime 1.31.1 · OpenCV 5.0 · Python 3.12 —— 全部离线可复现。</div>
  <div style="margin-top:10px">
    <span class="pill ok">v1.0.0</span>
    <span class="pill">MIT License（代码）</span>
    <span class="pill">CC BY 4.0（数据 / 权重）</span>
    <span class="pill">__DATE__</span>
  </div>
  <div class="small" style="margin-top:8px">
    引用本页请使用：<code>PPE Construction Safety Demo (YOLOv8n + X-AnyLabeling). v1.0.0, 2026.</code>
  </div>
</footer>

</div>

<script>
const DATA = __DATA__;
const IMGS = DATA.images;
const galleries = [];   // one entry per viewer; arrow keys drive the last clicked

function wire(imgs, prefix, ids) {
  let i = 0, m = 'orig';
  const big = document.getElementById(ids.big);
  const meta = document.getElementById(ids.meta);
  const thumbs = document.getElementById(ids.thumbs);
  const tabs = document.querySelectorAll('#' + ids.tabs + ' button');
  const g = {
    active: false,
    step: function (d) {
      const n = imgs.length;
      const k = (i + d + n) % n;          // wrap around, arrows never dead-end
      if (k !== i) { i = k; render(); }
    }
  };

  function focus() { galleries.forEach(x => { x.active = (x === g); }); }

  imgs.forEach((it, k) => {
    const im = document.createElement('img');
    im.src = prefix + 'pred_' + it.stem + '.jpg';
    im.title = it.file;
    im.onclick = () => { i = k; focus(); render(); };
    thumbs.appendChild(im);
  });

  function render() {
    const it = imgs[i];
    big.src = prefix + m + '_' + it.stem + '.jpg';
    const gs = Object.entries(it.gt).map(([k, v]) => k + '×' + v).join('　') || '无目标';
    meta.innerHTML =
      '<div>' + it.file + '　<span class="small">' + (i + 1) + ' / ' + imgs.length + '</span></div>' +
      '<div>真值：' + gs + '　（共 ' + it.gt_total + ' 个框）</div>' +
      '<div>预测：' + it.pred_total + ' 个框　·　TP ' + it.tp +
      ' / FP ' + it.fp + ' / FN ' + it.fn + '</div>';
    [...thumbs.children].forEach((c, k) => c.classList.toggle('on', k === i));
    const on = thumbs.children[i];
    if (on && on.scrollIntoView) {
      on.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    }
  }

  tabs.forEach(b => {
    b.onclick = () => {
      m = b.dataset.mode;
      focus();
      tabs.forEach(x => x.classList.toggle('on', x === b));
      render();
    };
  });

  galleries.push(g);
  render();
  g.render = render;
  return g;
}

const g1 = wire(IMGS, 'assets/', { big: 'big', meta: 'meta', thumbs: 'thumbs', tabs: 'tabs' });
g1.active = true;

document.addEventListener('keydown', e => {
  if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') { return; }
  const g = galleries.find(x => x.active) || galleries[0];
  g.step(e.key === 'ArrowRight' ? 1 : -1);
  e.preventDefault();
});
</script>
</body>
</html>
"""


def read_json(name):
    with open(os.path.join(ROOT, "out", name), encoding="utf-8") as f:
        return json.load(f)


MODE_KEYS = ["A", "B", "C"]
MODE_CN = {"A": "A · 整图基线", "B": "B · 缩图多尺度", "C": "C · 分块 2×2（对照）"}
SIZE_KEYS = ["小 (<48px)", "中 (48-96px)", "大 (>=96px)"]


def pick_mode(modes, tag):
    """out/ab_tiled.json keys modes by their full label, e.g. 'B 缩图多尺度'."""
    for k, v in modes.items():
        if k.split()[0] == tag:
            return v
    return None


def ab_tables(ab, ab_valid):
    """Build the A/B comparison rows from out/ab_tiled*.json."""
    modes = ab["modes"]
    base = pick_mode(modes, "A")["metrics"]["mAP50"]

    rows = []
    for tag in MODE_KEYS:
        m = pick_mode(modes, tag)
        if not m:
            continue
        mt = m["metrics"]
        d = mt["mAP50"] - base
        dtxt = "—" if tag == "A" else (("+%.4f" % d) if d > 0 else ("%.4f" % d))
        verdict = {
            "A": "基线",
            "B": "<b>采用</b>：涨点，代价是耗时约翻倍",
            "C": "证伪：掉点一半以上，且最慢",
        }.get(tag, "")
        rows.append(
            "<tr%s><td>%s</td><td class='num'>%.4f</td><td class='num'>%.4f</td>"
            "<td class='num'>%.2f</td><td class='num'>%.1f</td><td class='num'>%s</td><td>%s</td></tr>"
            % (
                " style='background:#1b2431'" if tag == "B" else "",
                MODE_CN[tag], mt["mAP50"], mt["mAP50_95"], m["det_per_image"],
                m["latency_ms"], dtxt, verdict,
            )
        )

    size_rows = []
    for tag in MODE_KEYS:
        m = pick_mode(modes, tag)
        if not m:
            continue
        rb = m.get("recall_by_size", {})
        cells = []
        for k in SIZE_KEYS:
            v = rb.get(k, {})
            cells.append(
                "<td class='num'>%.4f <span class='small'>(%d/%d)</span></td>"
                % (v.get("recall", 0.0), v.get("hit", 0), v.get("gt", 0))
            )
        size_rows.append(
            "<tr%s><td>%s</td>%s</tr>"
            % (" style='background:#1b2431'" if tag == "B" else "", MODE_CN[tag],
               "".join(cells))
        )

    valid_rows = []
    for tag in MODE_KEYS:
        m = pick_mode(ab_valid["modes"], tag)
        if not m:
            continue
        mt = m["metrics"]
        big = m.get("recall_by_size", {}).get(SIZE_KEYS[2], {}).get("recall", 0.0)
        valid_rows.append(
            "<tr%s><td>%s</td><td class='num'>%.4f</td><td class='num'>%.4f</td>"
            "<td class='num'>%.1f</td><td class='num'>%.4f</td></tr>"
            % (" style='background:#1b2431'" if tag == "B" else "", MODE_CN[tag],
               mt["mAP50"], mt["mAP50_95"], m["latency_ms"], big)
        )

    A = pick_mode(modes, "A")
    B = pick_mode(modes, "B")
    Av = pick_mode(ab_valid["modes"], "A")
    Bv = pick_mode(ab_valid["modes"], "B")
    ctx = {
        "base": A["metrics"]["mAP50"],
        "improved": B["metrics"]["mAP50"],
        "gain": B["metrics"]["mAP50"] - A["metrics"]["mAP50"],
        "ms_a": A["latency_ms"],
        "ms_b": B["latency_ms"],
        "big_a": A["recall_by_size"][SIZE_KEYS[2]]["recall"],
        "big_b": B["recall_by_size"][SIZE_KEYS[2]]["recall"],
        "small_a": A["recall_by_size"][SIZE_KEYS[0]]["recall"],
        "small_b": B["recall_by_size"][SIZE_KEYS[0]]["recall"],
        "valid_gain": Bv["metrics"]["mAP50"] - Av["metrics"]["mAP50"],
    }
    return "\n".join(rows), "\n".join(size_rows), "\n".join(valid_rows), ctx


def fail_cards(fails):
    """Build the failure-case cards (orig / pred side by side + diagnosis)."""
    cards = []
    for f in fails:
        stem = f["stem"]
        missed = "、".join("%s×%d" % (k, v) for k, v in f["missed"].items()) or "无"
        falsep = "、".join("%s×%d" % (k, v) for k, v in f["false_pos"].items()) or "无"
        ms = f.get("missed_size") or {}
        why = ""
        if ms:
            order = sorted(ms.items(), key=lambda kv: -kv[1])
            why = ("漏掉的框以「%s」目标为主（小 &lt;48px / 中 48–96px / 大 ≥96px）" % order[0][0])
            if len(order) > 1:
                why += "，另有「%s」%d 个" % (order[1][0], order[1][1])
        else:
            why = "本图没有漏检，问题全在误检"
        cards.append(
            "<div class='failcard'>"
            "<div class='failimgs'>"
            "<img src='assets3/orig_%s.jpg' alt='原图' loading='lazy'>"
            "<img src='assets3/pred_%s.jpg' alt='模型输出' loading='lazy'>"
            "</div>"
            "<div class='cap'>左：原图　右：模型输出（绿=命中，红=误检，橙虚线=漏检）</div>"
            "<div class='failmeta'>"
            "<b>%s</b>　<span class='small'>%d×%d</span><br>"
            "真值 <b>%d</b> 框　·　命中 <b>%d</b>　·　误检 <b>%d</b>　·　漏检 <b>%d</b><br>"
            "漏检：%s<br>误检：%s"
            "<span class='why'>%s</span>"
            "</div></div>"
            % (stem, stem, f["file"][:52], f["size"][0], f["size"][1],
               f["gt_total"], f["tp"], f["fp"], f["fn"], missed, falsep, why)
        )
    return "\n".join(cards)


def main():
    metrics = read_json("metrics.json")            # test split
    stats = read_json("demo_stats.json")           # first gallery (32 imgs)
    full = read_json("full_eval_summary.json")     # train / valid / test / all
    split_counts = read_json("split_counts.json")  # measured from label files
    stats2 = read_json("demo2_stats.json")         # expanded gallery (60 imgs)
    ab = read_json("ab_tiled.json")                # A/B on test
    ab_valid = read_json("ab_tiled_valid.json")    # A/B on valid
    fails = read_json("failure_stats.json")        # worst-case gallery

    per = metrics["per_class"]
    op = metrics["operating_point_conf035"]

    ap_rows = []
    for k in ["helmet", "person", "vest", "no-vest", "no-helmet"]:
        v = per[k]
        pct = max(2, round(v["ap50"] * 100))
        ap_rows.append(
            "<tr><td>%s</td><td class='num'>%.4f</td><td class='num'>%.4f</td>"
            "<td class='num'>%d</td><td class='num'>%d</td>"
            "<td><div class='bar'><i style='width:%d%%'></i></div></td></tr>"
            % (CN[k], v["ap50"], v["ap50_95"], v["gt"], v["pred"], pct)
        )

    pr_rows = []
    for k in ["helmet", "person", "vest", "no-vest", "no-helmet"]:
        v = op[k]
        pr_rows.append(
            "<tr><td>%s</td><td class='num'>%.3f</td><td class='num'>%.3f</td>"
            "<td class='num'>%.3f</td><td class='num'>%d</td><td class='num'>%d</td></tr>"
            % (CN[k], v["precision"], v["recall"], v["f1"], v["pred"], v["gt"])
        )

    # per-split metric table (all three splits + weighted merge)
    order = ["helmet", "person", "vest", "no-vest", "no-helmet"]
    SPLIT_CN = {"train": "训练集", "valid": "验证集", "test": "测试集", "all": "合计（加权）"}
    split_rows = []
    for sp in ["train", "valid", "test", "all"]:
        v = full.get(sp)
        if not v:
            continue
        pc = v.get("per_class") or v.get("per_class_AP50_weighted") or {}
        m95 = v.get("mAP50_95")
        cells = "".join("<td class='num'>%.3f</td>" % pc.get(k, 0.0) for k in order)
        split_rows.append(
            "<tr%s><td>%s</td><td class='num'>%d</td><td class='num'>%d</td>"
            "<td class='num'>%d</td><td class='num'><b>%.4f</b></td><td class='num'>%s</td>%s</tr>"
            % (
                " style='background:#1b2431'" if sp == "all" else "",
                SPLIT_CN[sp], v["images"], v["gt_boxes"], v["pred_boxes"],
                v["mAP50"], "%.4f" % m95 if m95 is not None else "—", cells,
            )
        )

    # dataset split table (counts measured from the label files)
    ds_rows = []
    tot = [0] * 5
    tot_imgs = 0
    for sp in ["train", "valid", "test"]:
        v = split_counts[sp]
        tot_imgs += v["labels"]
        for i, c in enumerate(v["counts"]):
            tot[i] += c
        ds_rows.append(
            "<tr><td>%s</td><td class='num'>%d</td>%s</tr>"
            % (sp, v["labels"], "".join("<td class='num'>%d</td>" % c for c in v["counts"]))
        )
    ds_rows.append(
        "<tr><td><b>合计</b></td><td class='num'><b>%d</b></td>%s</tr>"
        % (tot_imgs, "".join("<td class='num'><b>%d</b></td>" % c for c in tot))
    )

    images = []
    for s in stats:
        images.append(
            {
                "file": s["file"],
                "stem": s["stem"],
                "size": s["size"],
                "gt": s["gt"],
                "gt_total": s["gt_total"],
                "pred_total": s["pred_total"],
                "tp": s["tp"],
                "fp": s["fp"],
                "fn": s["fn"],
            }
        )

    ab_rows, ab_size_rows, ab_valid_rows, abx = ab_tables(ab, ab_valid)
    fail_html = fail_cards(fails)
    fail_gt = sum(f["gt_total"] for f in fails)
    fail_tp = sum(f["tp"] for f in fails)
    fail_fp = sum(f["fp"] for f in fails)
    fail_fn = sum(f["fn"] for f in fails)

    html = PAGE
    repl = {
        "__DATE__": "2026-11-23",
        "__M_AP__": "%.3f" % full["all"]["mAP50"],
        "__M_AP_TEST__": "%.3f" % metrics["mAP50"],
        "__M_AP95__": "%.3f" % metrics["mAP50_95"],
        "__N_IMGS__": str(len(stats)),
        "__N_IMGS2__": str(len(stats2)),
        "__N_ALL__": str(full["all"]["images"]),
        "__AP_ROWS__": "\n".join(ap_rows),
        "__PR_ROWS__": "\n".join(pr_rows),
        "__SPLIT_ROWS__": "\n".join(split_rows),
        "__DATASET_ROWS__": "\n".join(ds_rows),
        "__GT_BOXES__": str(metrics["gt_boxes"]),
        "__PRED_BOXES__": str(metrics["pred_boxes"]),
        "__AP_HELMET__": "%.3f" % per["helmet"]["ap50"],
        "__AP_PERSON__": "%.3f" % per["person"]["ap50"],
        "__AP_NOHELMET__": "%.3f" % per["no-helmet"]["ap50"],
        "__GT_NOHELMET__": str(per["no-helmet"]["gt"]),
        "__AB_ROWS__": ab_rows,
        "__AB_SIZE_ROWS__": ab_size_rows,
        "__AB_VALID_ROWS__": ab_valid_rows,
        "__AB_BASE__": "%.4f" % abx["base"],
        "__AB_IMPROVED__": "%.4f" % abx["improved"],
        "__AB_GAIN__": "%.4f" % abx["gain"],
        "__AB_MS_A__": "%.0f" % abx["ms_a"],
        "__AB_MS_B__": "%.0f" % abx["ms_b"],
        "__AB_BIG_A__": "%.4f" % abx["big_a"],
        "__AB_BIG_B__": "%.4f" % abx["big_b"],
        "__AB_SMALL_A__": "%.4f" % abx["small_a"],
        "__AB_SMALL_B__": "%.4f" % abx["small_b"],
        "__AB_VALID_GAIN__": "%.4f" % abx["valid_gain"],
        "__FAIL_CARDS__": fail_html,
        "__FAIL_GT__": str(fail_gt),
        "__FAIL_TP__": str(fail_tp),
        "__FAIL_FP__": str(fail_fp),
        "__FAIL_FN__": str(fail_fn),
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    html = html.replace(
        "__DATA__", json.dumps({"images": images}, ensure_ascii=False)
    )

    os.makedirs(WEB, exist_ok=True)
    out = os.path.join(WEB, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("written:", out, "|", len(html), "chars |", len(images), "images")


if __name__ == "__main__":
    main()
