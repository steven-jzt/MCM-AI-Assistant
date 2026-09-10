#!/usr/bin/env python3
"""
一键出图模板渲染器 — render_template.py
=========================================
参考 mathmodel-kit 的 render_template.py 设计：每个模板 id 对应一种论文级图表，
一条命令渲染 PNG(300 DPI) + SVG + PDF 三格式，附确定性示例数据（seed=42）。

用法：
    python render_template.py <id>                 # 渲染单个模板到 figures/
    python render_template.py <id> --out results   # 指定输出目录
    python render_template.py --list               # 列出全部模板
    python render_template.py --all                # 全量渲染
"""

import os
import sys

# Windows 中文控制台默认 GBK，无法编码 — 等 Unicode 符号，统一转 UTF-8 输出避免崩溃
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# sys.path bootstrap：保证从任意 CWD 都能 import 项目根目录下的 utils.visual
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import numpy as np
from scipy.cluster.hierarchy import linkage
from utils import visual
from utils import diagram


# ── 确定性示例数据（seed=42）────────────────────────────────────────

_RNG = np.random.default_rng(42)

_X = np.linspace(0, 4 * np.pi, 50)
_Y1 = np.sin(_X) + _RNG.normal(0, 0.1, 50)
_Y2 = np.cos(_X) + _RNG.normal(0, 0.1, 50)

_ACTUAL = _RNG.normal(0, 1, 120)
_PRED = _ACTUAL + _RNG.normal(0, 0.3, 120)

_FITTED = np.linspace(0, 10, 120)
_RESID = _RNG.normal(0, 1, 120)

_GA_HISTORY = np.minimum.accumulate(5 + _RNG.normal(0, 1, 80))

_Y_TRUE = _RNG.integers(0, 2, 200)
_Y_SCORE = np.clip(_Y_TRUE * 0.8 + _RNG.normal(0.5, 0.25, 200), 0, 1)

_GROUPS = {
    "组1": _RNG.normal(0, 1, 200),
    "组2": _RNG.normal(1, 1.5, 200),
    "组3": _RNG.normal(2, 1, 150),
}

_X2D = _RNG.normal(0, 1, (120, 2))
_CLUSTER_LABELS = (_X2D[:, 0] > 0).astype(int)

_Z_LINKAGE = linkage(_RNG.normal(0, 1, (12, 2)), method="ward")

_R_MATRIX = np.array([
    [1.0, 0.72, -0.35],
    [0.72, 1.0, -0.18],
    [-0.35, -0.18, 1.0],
])

# ── 框架图示例 content（确定性 dict，驱动 utils.diagram）────────────

_ROADMAP = {
    "title": "城市交通拥堵治理研究技术路线",
    "bands": [
        {"head": "提出问题", "items": ["拥堵现状分析", "问题界定与假设", "数据采集"]},
        {"head": "数据与指标", "items": ["数据清洗", "指标体系构建", "缺失值处理"]},
        {"head": "方法与机制", "items": ["交通流模型", "GM(1,1) 预测", "优化模型"]},
        {"head": "结果对比", "items": ["模型验证", "方案对比", "误差分析"]},
        {"head": "评价推广", "items": ["方案评价", "灵敏度分析", "结论建议"]},
    ],
}

_FRAMEWORK = {
    "title": "研究框架",
    "stages": [
        {"head": "数据准备", "content": ["数据采集", "数据清洗", "特征构造"], "methods": ["描述统计", "缺失值处理"]},
        {"head": "模型构建", "content": ["预测模型", "优化模型"], "methods": ["GM(1,1)", "遗传算法"]},
        {"head": "结果分析", "content": ["模型验证", "方案对比"], "methods": ["交叉验证", "误差分析"]},
    ],
}

_STAGEFLOW = {
    "title": "执行流程",
    "stages": [
        {"head": "阶段一", "steps": ["数据预处理", "指标构建", "权重确定"]},
        {"head": "阶段二", "steps": ["模型求解", "参数寻优", "结果输出"]},
        {"head": "阶段三", "steps": ["结果验证", "敏感性分析", "方案评价"]},
    ],
}

_TASKFLOW = {
    "title": "课题任务拆解",
    "tasks": [
        {"head": "任务一：预处理", "steps": ["清洗", "特征", "切分"]},
        {"head": "任务二：建模", "steps": ["选模型", "训练", "调参"]},
        {"head": "任务三：求解", "steps": ["寻优", "对比", "输出"]},
        {"head": "任务四：评价", "steps": ["验证", "敏感性", "结论"]},
    ],
}

_PROBLEM_FLOW = {
    "title": "问题分析",
    "root": "城市交通拥堵治理",
    "branches": ["问题一：交通流预测", "问题二：最优信号配时", "问题三：方案评价"],
    "bottom": "综合解决方案",
    "feedback": "反馈修正",
}


# ── 模板注册表 ─────────────────────────────────────────────────────

TEMPLATES = {
    # ── 基础图型 ──
    "line": {
        "name": "折线图",
        "description": "单序列折线图，展示趋势。",
        "builder": lambda out: visual.line_chart(
            _X, _Y1, xlabel="x", ylabel="sin(x)", title="折线图",
            save_path=os.path.join(out, "line.png")),
    },
    "multi_line": {
        "name": "多折线图",
        "description": "多序列折线对比，自动图例。",
        "builder": lambda out: visual.multi_line_chart(
            _X, {"sin(x)": _Y1, "cos(x)": _Y2}, xlabel="x", ylabel="值", title="多折线图",
            save_path=os.path.join(out, "multi_line.png")),
    },
    "bar": {
        "name": "柱状图",
        "description": "单序列柱状图，柱顶标注数值。",
        "builder": lambda out: visual.bar_chart(
            ["北京", "上海", "广州", "深圳", "杭州"], [40000, 44000, 28000, 32000, 21000],
            title="城市 GDP（亿元）", save_path=os.path.join(out, "bar.png")),
    },
    "grouped_bar": {
        "name": "分组柱状图",
        "description": "多组柱状对比。",
        "builder": lambda out: visual.grouped_bar_chart(
            ["2020", "2021", "2022", "2023"],
            {"产品A": [120, 135, 148, 162], "产品B": [80, 95, 110, 130], "产品C": [45, 52, 60, 75]},
            xlabel="年份", ylabel="销售额（万元）", title="分类销售对比",
            save_path=os.path.join(out, "grouped_bar.png")),
    },
    "scatter": {
        "name": "散点图",
        "description": "散点图（可选颜色映射）。",
        "builder": lambda out: visual.scatter_plot(
            _RNG.normal(0, 1, 200), _RNG.normal(2, 1.5, 200), c=_RNG.random(200),
            xlabel="X", ylabel="Y", title="散点图（颜色映射）",
            save_path=os.path.join(out, "scatter.png")),
    },
    "heatmap": {
        "name": "热力图",
        "description": "相关性矩阵热力图（RdBu_r）。",
        "builder": lambda out: visual.heatmap(
            _R_MATRIX, title="相关系数热力图", save_path=os.path.join(out, "heatmap.png")),
    },
    "radar": {
        "name": "雷达图",
        "description": "多维度指标雷达图（≤6 维）。",
        "builder": lambda out: visual.radar_chart(
            ["创新力", "成本控制", "交付速度", "产品质量", "客户满意度", "市场份额"],
            [0.85, 0.62, 0.91, 0.78, 0.88, 0.65], title="企业竞争力雷达图",
            save_path=os.path.join(out, "radar.png")),
    },
    "hist": {
        "name": "直方图",
        "description": "分布直方图 + KDE 密度曲线。",
        "builder": lambda out: visual.histogram(
            _RNG.normal(100, 15, 500), bins=30, density=True,
            xlabel="分数", ylabel="密度", title="考试成绩分布",
            save_path=os.path.join(out, "hist.png")),
    },
    "qq": {
        "name": "QQ 图",
        "description": "正态性检验 QQ 图。",
        "builder": lambda out: visual.qq_plot(
            _RNG.normal(0, 1, 200), title="正态性 QQ 图",
            save_path=os.path.join(out, "qq.png")),
    },
    "line_ci": {
        "name": "置信区间折线图",
        "description": "折线图 + 置信区间填充。",
        "builder": lambda out: visual.line_with_ci(
            _X, _Y1, _Y1 - 0.15, _Y1 + 0.15, xlabel="x", ylabel="sin(x)",
            title="折线图（含 95% CI）", save_path=os.path.join(out, "line_ci.png")),
    },
    "dual_axis": {
        "name": "双 Y 轴图",
        "description": "不同量纲双序列对比（谨慎使用）。",
        "builder": lambda out: visual.dual_axis_chart(
            _X, _Y1, _Y2 * 100, y1_label="sin(x)", y2_label="100×cos(x)",
            xlabel="x", title="双 Y 轴对比", save_path=os.path.join(out, "dual_axis.png")),
    },
    # ── 高级图型 ──
    "convergence": {
        "name": "迭代收敛曲线",
        "description": "遗传算法/模拟退火收敛曲线，标注最优值。",
        "builder": lambda out: visual.convergence_chart(
            _GA_HISTORY, title="遗传算法收敛曲线", save_path=os.path.join(out, "convergence.png")),
    },
    "pred_vs_actual": {
        "name": "预测 vs 实际",
        "description": "预测-实际散点 + 45° 参考线 + R²/RMSE。",
        "builder": lambda out: visual.prediction_vs_actual(
            _ACTUAL, _PRED, save_path=os.path.join(out, "pred_vs_actual.png")),
    },
    "residual_panel": {
        "name": "残差诊断面板",
        "description": "残差-拟合值散点 + 残差分布（回归诊断）。",
        "builder": lambda out: visual.residual_panel(
            _FITTED, _RESID, save_path=os.path.join(out, "residual_panel.png")),
    },
    "tornado": {
        "name": "灵敏度龙卷风图",
        "description": "关键参数敏感性扫描（按影响范围降序）。",
        "builder": lambda out: visual.tornado_chart(
            ["参数α", "参数β", "参数γ", "参数δ"], [10, 20, 5, 8], [14, 26, 9, 9],
            title="灵敏度龙卷风图", save_path=os.path.join(out, "tornado.png")),
    },
    "taylor": {
        "name": "泰勒图",
        "description": "多模型 R / 标准差 / RMS 三统计量比较。",
        "builder": lambda out: visual.taylor_diagram(
            [0.8, 1.1, 1.3], [0.95, 0.88, 0.75], labels=["模型A", "模型B", "模型C"],
            save_path=os.path.join(out, "taylor.png")),
    },
    "roc": {
        "name": "ROC 曲线",
        "description": "二分类 ROC 曲线 + AUC。",
        "builder": lambda out: visual.roc_curve(
            _Y_TRUE, _Y_SCORE, save_path=os.path.join(out, "roc.png")),
    },
    "raincloud": {
        "name": "云雨图",
        "description": "半边小提琴 + 抖动散点 + 箱线（分布对比）。",
        "builder": lambda out: visual.raincloud(
            _GROUPS, save_path=os.path.join(out, "raincloud.png")),
    },
    "cluster_scatter": {
        "name": "聚类散点图",
        "description": "聚类二维投影 + 质心 + 凸包。",
        "builder": lambda out: visual.cluster_scatter(
            _X2D, _CLUSTER_LABELS, save_path=os.path.join(out, "cluster_scatter.png")),
    },
    "dendrogram": {
        "name": "层次聚类树状图",
        "description": "层次聚类 linkage 树状图。",
        "builder": lambda out: visual.dendrogram(
            _Z_LINKAGE, save_path=os.path.join(out, "dendrogram.png")),
    },
    "elbow": {
        "name": "肘部法则",
        "description": "不同 K 的簇内平方和，用于选聚类数。",
        "builder": lambda out: visual.elbow_curve(
            [100, 60, 40, 30, 25, 22], save_path=os.path.join(out, "elbow.png")),
    },
    # ── 框架图（utils.diagram，非数据型图示）──
    "diagram_roadmap": {
        "name": "技术路线图",
        "description": "竖版五带技术路线图（提出问题→评价推广）。",
        "builder": lambda out: diagram.diagram_roadmap(
            _ROADMAP, save_path=os.path.join(out, "roadmap.png")),
    },
    "diagram_framework": {
        "name": "研究框架图",
        "description": "三栏研究框架图（阶段/内容/方法）。",
        "builder": lambda out: diagram.diagram_framework(
            _FRAMEWORK, save_path=os.path.join(out, "framework.png")),
    },
    "diagram_stageflow": {
        "name": "阶段流程图",
        "description": "三栏阶段流程图（实色标题条+步骤流）。",
        "builder": lambda out: diagram.diagram_stageflow(
            _STAGEFLOW, save_path=os.path.join(out, "stageflow.png")),
    },
    "diagram_taskflow": {
        "name": "任务流水线图",
        "description": "横版任务流水线（16:9，课题拆解）。",
        "builder": lambda out: diagram.diagram_taskflow(
            _TASKFLOW, save_path=os.path.join(out, "taskflow.png")),
    },
    "diagram_problem_flow": {
        "name": "问题分析流程图",
        "description": "总分布局问题分析图（第二章必插）。",
        "builder": lambda out: diagram.diagram_problem_flow(
            _PROBLEM_FLOW, save_path=os.path.join(out, "problem_flow.png")),
    },
}


def render_template(template_id: str, out_dir: str = "figures") -> str:
    """渲染单个模板，输出 PNG + SVG + PDF 三格式。

    Returns
    -------
    png_path : str
    """
    if template_id not in TEMPLATES:
        raise KeyError(f"未知模板 '{template_id}'，可用 --list 查看全部模板。")
    os.makedirs(out_dir, exist_ok=True)

    old_formats = visual.SAVE_FORMATS
    visual.SAVE_FORMATS = ("png", "svg", "pdf")
    try:
        return TEMPLATES[template_id]["builder"](out_dir)
    finally:
        visual.SAVE_FORMATS = old_formats


def _print_list():
    print("=" * 62)
    print("可用出图模板")
    print("=" * 62)
    for tid, meta in TEMPLATES.items():
        print(f"  {tid:<16} {meta['name']}  —  {meta['description']}")
    print("=" * 62)
    print(f"共 {len(TEMPLATES)} 个模板。")


def _print_rendered(tid: str, png_path: str):
    base, _ = os.path.splitext(png_path)
    meta = TEMPLATES[tid]
    print(f"[OK] {meta['name']} → {png_path}")
    for ext in ("svg", "pdf"):
        p = f"{base}.{ext}"
        if os.path.exists(p):
            print(f"      └─ {p}")
    if not os.path.exists(f"{base}.svg"):
        print("      ⚠ 未找到 SVG（图型可能不支持）")
    if not os.path.exists(f"{base}.pdf"):
        print("      ⚠ 未找到 PDF（图型可能不支持）")


def _render_all(out_dir: str):
    failed = []
    for tid in TEMPLATES:
        try:
            path = render_template(tid, out_dir)
            _print_rendered(tid, path)
        except Exception as e:  # noqa: BLE001 —— 单个模板失败不阻断其余
            failed.append((tid, str(e)))
            print(f"[FAIL] {tid}: {e}")
    print("-" * 62)
    print(f"完成：{len(TEMPLATES) - len(failed)}/{len(TEMPLATES)} 成功")
    if failed:
        print("失败:")
        for tid, err in failed:
            print(f"  {tid}: {err}")


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="一键出图模板渲染器")
    parser.add_argument("template", nargs="?", help="模板 id（见 --list）")
    parser.add_argument("--list", action="store_true", help="列出全部模板")
    parser.add_argument("--all", action="store_true", help="渲染全部模板")
    parser.add_argument("--out", default="figures", help="输出目录（默认 figures）")
    args = parser.parse_args(argv)

    if args.list:
        _print_list()
        return 0
    if args.all:
        _render_all(args.out)
        return 0
    if not args.template:
        parser.print_help()
        return 1

    try:
        path = render_template(args.template, args.out)
    except KeyError as e:
        print(f"错误: {e}", file=sys.stderr)
        _print_list()
        return 1
    _print_rendered(args.template, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
