"""
框架图模块 — diagram.py
========================
用 matplotlib 渲染数学建模论文的「非数据型图示」：技术路线图、研究框架图、
阶段流程图、任务流水线图、问题分析流程图等。

与 `utils/visual.py`（数据图）分工：数据图讲「效果」，框架图讲「逻辑」。

设计要点：
- 像素坐标系（y 轴反转，原点在左上），画布尺寸即像素尺寸；
- dict 驱动，可序列化为 JSON，可复现；
- 中文断行 + 字宽预算校验（全角≈字号、半角≈字号/2），超框直接报错而非默默溢出；
- 复用 `visual._save_figure` / `visual.SAVE_FORMATS`，自动获得 PNG(300DPI)+SVG+PDF 三格式。

参考实现（思路借鉴，非拷贝）：Escap1ng/mathmodel-kit 的 mathmodel-diagram 技能
（common.py 基元 + 五套版式模板）。
"""

import os
import sys
import unicodedata

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

# sys.path bootstrap：保证直接运行脚本或从任意 CWD 都能 import utils.visual
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils.visual import get_color_palette, _save_figure

# ============================================================================
# 配色（学术蓝灰系，与数据图的色盲配色区分，适合示意图）
# ============================================================================

INK = "#333333"          # 主文字/描边
MUTED = "#6b7280"        # 次要文字
PAPER = "#ffffff"        # 盒子填充
BAND = {
    "fill": "#eef3fb", "stroke": "#5b93bd", "accent": "#b6d8f6", "head": "#4874cc",
}                          # 主蓝色系（技术路线图各带）
GROUP = {"fill": "#f4f4f4", "stroke": "#9a9a9a"}  # 分组虚线框
FEEDBACK = "#c96a4b"       # 反馈虚线色（暖色，区别于正向箭头）

# 备选色系（多阶段时轮换）
STAGE_COLORS = [
    {"head": "#4874cc", "fill": "#eef3fb", "stroke": "#5b93bd"},
    {"head": "#2f8f83", "fill": "#e9f6f3", "stroke": "#5da396"},
    {"head": "#c07a3c", "fill": "#fbf1e6", "stroke": "#c99a63"},
    {"head": "#8a5bb5", "fill": "#f3edfa", "stroke": "#a98bc4"},
    {"head": "#c0526b", "fill": "#fbeef1", "stroke": "#c58293"},
]

DASH = (0, (4, 3))


# ============================================================================
# 画布
# ============================================================================

def _pt(fs_px: float) -> float:
    """像素字号 → pt（100 dpi 画布下 1px ≈ 0.75pt）。"""
    return fs_px * 0.75


def setup_canvas(w_px: float, h_px: float):
    """建立像素坐标系画布：原点左上、y 向下、1 数据单位 = 1 像素。"""
    fig, ax = plt.subplots(figsize=(w_px / 100.0, h_px / 100.0), dpi=100)
    ax.set_xlim(0, w_px)
    ax.set_ylim(h_px, 0)          # y 反转
    ax.axis("off")
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    return fig, ax


# ============================================================================
# 中文字宽预算
# ============================================================================

def char_width(ch: str) -> float:
    """单字符宽度系数：全角（东亚宽 F/W）记 1.0，其余记 0.5。"""
    return 1.0 if unicodedata.east_asian_width(ch) in ("F", "W") else 0.5


def text_width(text: str, fs: float) -> float:
    """估算文本渲染宽度（像素）。全角 ≈ fs，半角 ≈ fs/2。"""
    return sum(char_width(c) for c in text) * fs


def lines_of(text: str, per_line: int) -> list:
    """把长文本按每行字符数切分（per_line 为「等效半角字符」预算的折算）。"""
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if sum(char_width(c) for c in cur) >= per_line * 0.5 and ch not in "\n":
            lines.append(cur)
            cur = ""
    if cur.strip() or not lines:
        lines.append(cur)
    return [ln.strip() for ln in lines if ln.strip()]


def check_text_fits(text: str, box_w: float, fs: float, pad: float = 10.0) -> None:
    """校验文本（含换行）是否能放进指定宽度，超框则抛错。"""
    for ln in str(text).split("\n"):
        if text_width(ln, fs) > box_w - pad:
            raise ValueError(
                f"文字超框：『{ln}』宽 {text_width(ln, fs):.0f}px，"
                f"盒内可用 {box_w - pad:.0f}px（字号 {fs}px）"
            )


# ============================================================================
# 图元
# ============================================================================

def _put_text(ax, x, y, w, h, text, fs=16, fc=INK, bold=False, pad=4.0):
    """在 (x, y, w, h) 盒子内居中放置多行文本，逐行做字宽校验。"""
    if text is None:
        return
    lines = str(text).split("\n")
    for ln in lines:
        if text_width(ln, fs) > w - 2 * pad:
            raise ValueError(f"文字超框：『{ln}』宽 {text_width(ln, fs):.0f}px，盒宽 {w:.0f}px")
    total_h = len(lines) * (fs + 3)
    y_start = y + h / 2 - total_h / 2 + fs / 2
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, y_start + i * (fs + 3), ln, fontsize=_pt(fs),
                color=fc, ha="center", va="center", fontweight="bold" if bold else "normal",
                family="sans-serif", zorder=5)


def draw_box(ax, x, y, w, h, text=None, fill=PAPER, stroke=INK, fs=16, fc=INK,
             bold=False, arc=8, width=1.2, pad=4.0):
    """圆角矩形节点。"""
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle=f"round,pad=0,rounding_size={arc}",
                         linewidth=width, edgecolor=stroke, facecolor=fill, zorder=3)
    ax.add_patch(box)
    _put_text(ax, x, y, w, h, text, fs=fs, fc=fc, bold=bold, pad=pad)
    return box


def draw_diamond(ax, x, y, w, h, text=None, fill=PAPER, stroke=INK, fs=15,
                 fc=INK, width=1.2):
    """菱形（判断）节点。"""
    cx, cy = x + w / 2, y + h / 2
    pts = [(cx, y), (x + w, cy), (cx, y + h), (x, cy)]
    ax.add_patch(Polygon(pts, closed=True, linewidth=width, edgecolor=stroke,
                         facecolor=fill, zorder=3))
    _put_text(ax, x, y, w, h, text, fs=fs, fc=fc, pad=w * 0.18)
    return pts


def draw_hexagon(ax, x, y, w, h, text=None, fill=PAPER, stroke=INK, fs=15,
                 fc=INK, width=1.2):
    """六边形节点。"""
    notch = min(w, h) * 0.2
    pts = [(x + notch, y), (x + w - notch, y), (x + w, y + h / 2),
           (x + w - notch, y + h), (x + notch, y + h), (x, y + h / 2)]
    ax.add_patch(Polygon(pts, closed=True, linewidth=width, edgecolor=stroke,
                         facecolor=fill, zorder=3))
    _put_text(ax, x, y, w, h, text, fs=fs, fc=fc, pad=notch + 4)
    return pts


def draw_text(ax, x, y, w, h, text, fs=16, fc=INK, bold=False, ha="center", va="center"):
    """自由文本（不带盒子）。"""
    ax.text(x, y, text, fontsize=_pt(fs), color=fc, ha=ha, va=va,
            fontweight="bold" if bold else "normal", family="sans-serif", zorder=5)


def draw_dashed_rect(ax, x, y, w, h, color=MUTED, width=1.0, label=None, fs=14):
    """虚线分组框（可选左上角标签）。"""
    from matplotlib.patches import FancyBboxPatch
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=6",
                                linewidth=width, edgecolor=color, facecolor="none",
                                linestyle=DASH, zorder=1))
    if label:
        draw_text(ax, x + 8, y + 8, 0, 0, label, fs=fs, fc=MUTED, ha="left", va="top")


def draw_arrow(ax, pts, color=INK, width=1.4, head_size=6, linestyle="solid", zorder=2):
    """折线箭头。pts 为 [(x,y), ...] 折线点，末段画箭头。"""
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, linewidth=width, linestyle=linestyle,
            solid_capstyle="round", zorder=zorder)
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle="-|>", color=color, lw=width,
                                mutation_scale=head_size * 2, linestyle=linestyle),
                zorder=zorder + 1)


def draw_block_arrow(ax, x, y, w, h, text=None, fill=INK, fc="white", fs=16,
                     direction="down"):
    """块状箭头（粗箭头，表示阶段推进）。direction: down/right。"""
    if direction == "down":
        pts = [(x, y), (x + w, y), (x + w / 2, y + h), (x, y)]
    else:
        pts = [(x, y), (x + w, y + h / 2), (x, y + h), (x + w, y + h)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=fill, edgecolor="none", zorder=3))
    if text:
        cx = x + w / 2
        cy = y + h / 2 + (h / 4 if direction == "down" else 0)
        draw_text(ax, cx, cy, 0, 0, text, fs=fs, fc=fc, bold=True)


def draw_flag(ax, x, y, w, h, text=None, fill=BAND["accent"], stroke=BAND["stroke"],
              fs=17, fc=INK):
    """旗帜标签（左侧竖条 + 主体），用于带标题。"""
    ax.add_patch(FancyBboxPatch((x, y), 6, h, boxstyle="square,pad=0",
                                linewidth=0, edgecolor="none", facecolor=stroke, zorder=3))
    ax.add_patch(FancyBboxPatch((x + 6, y), w - 6, h,
                                boxstyle="round,pad=0,rounding_size=4",
                                linewidth=1.0, edgecolor=stroke, facecolor=fill, zorder=3))
    _put_text(ax, x + 6, y, w - 6, h, text, fs=fs, fc=fc, bold=True)


# ============================================================================
# 布局工具
# ============================================================================

def slots(a: float, b: float, n: int, gap: float = 0.0) -> list:
    """在 [a, b] 内均分 n 个等宽槽位，返回每个槽位的起点 x 列表。"""
    if n <= 0:
        return []
    total_gap = gap * (n - 1)
    w = (b - a - total_gap) / n
    return [a + i * (w + gap) for i in range(n)]


def _finish(fig, save_path):
    """统一收尾：保存多格式并关闭。"""
    fig.tight_layout(pad=0.5)
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 模板 1：五带技术路线图（竖版）
# ============================================================================

def diagram_roadmap(content: dict, save_path: str = "roadmap.png") -> str:
    """五带技术路线图（竖版 954×1296）。

    content 结构：
        {
            "title": "技术路线",            # 可选
            "bands": [
                {"head": "提出问题", "items": ["...", "...", "..."]},   # 1~4 项
                ...   # 共 5 个带
            ]
        }
    """
    W, H = 954, 1296
    fig, ax = setup_canvas(W, H)

    title = content.get("title")
    if title:
        draw_text(ax, W / 2, 46, 0, 0, title, fs=26, fc=INK, bold=True)

    bands = content.get("bands", [])
    if len(bands) != 5:
        raise ValueError(f"roadmap 需要 5 个 band，实际 {len(bands)} 个")

    band_top = 100
    band_h = 205
    band_gap = 38

    for i, band in enumerate(bands):
        ty = band_top + i * (band_h + band_gap)
        head = band.get("head", f"阶段 {i + 1}")
        items = band.get("items", [])
        if not 1 <= len(items) <= 4:
            raise ValueError(f"band{i + 1}.items 需 1~4 项，实际 {len(items)}")

        col = STAGE_COLORS[i % len(STAGE_COLORS)]

        # 左侧旗帜标题（竖排无，横排两行）
        draw_flag(ax, 60, ty, 170, band_h, head, fill=col["fill"], stroke=col["stroke"])

        # 右侧内容盒
        n = len(items)
        box_area_x0, box_area_x1 = 270, 894
        box_w = (box_area_x1 - box_area_x0 - (n - 1) * 20) / n
        box_h = 150
        by = ty + (band_h - box_h) / 2
        xs = slots(box_area_x0, box_area_x1, n, gap=20)
        for k, (bx, item) in enumerate(zip(xs, items)):
            draw_box(ax, bx, by, box_w, box_h, item, fill=col["fill"], stroke=col["stroke"],
                     fs=16, bold=False, arc=8)

        # 带间箭头
        if i < 4:
            nx = 145
            draw_arrow(ax, [(nx, ty + band_h), (nx, ty + band_h + band_gap)],
                       color=col["stroke"], width=1.6)

    return _finish(fig, save_path)


# ============================================================================
# 模板 2：三栏研究框架图
# ============================================================================

def diagram_framework(content: dict, save_path: str = "framework.png") -> str:
    """三栏研究框架图（左阶段链 / 中内容块 / 右方法清单）。

    content 结构：
        {
            "title": "研究框架",
            "stages": [
                {"head": "阶段一", "content": ["内容1", "内容2"], "methods": ["方法1", "方法2"]},
                ...   # 2~4 个阶段
            ]
        }
    """
    stages = content.get("stages", [])
    if not 2 <= len(stages) <= 4:
        raise ValueError(f"framework 需要 2~4 个阶段，实际 {len(stages)} 个")

    W = 1026
    band_gap = 30
    band_h = 150
    H = 140 + len(stages) * (band_h + band_gap) + 40
    fig, ax = setup_canvas(W, H)

    title = content.get("title")
    if title:
        draw_text(ax, W / 2, 40, 0, 0, title, fs=26, fc=INK, bold=True)

    col_l, col_m, col_r = 60, 300, 690
    w_l, w_m, w_r = 200, 350, 270

    # 表头
    draw_text(ax, col_l + w_l / 2, 90, 0, 0, "研究阶段", fs=16, fc=MUTED, bold=True)
    draw_text(ax, col_m + w_m / 2, 90, 0, 0, "研究内容", fs=16, fc=MUTED, bold=True)
    draw_text(ax, col_r + w_r / 2, 90, 0, 0, "方法工具", fs=16, fc=MUTED, bold=True)

    y0 = 120
    for i, st in enumerate(stages):
        sy = y0 + i * (band_h + band_gap)
        col = STAGE_COLORS[i % len(STAGE_COLORS)]

        # 左：阶段链节点
        draw_box(ax, col_l, sy, w_l, band_h, st.get("head", f"阶段 {i + 1}"),
                 fill=col["head"], stroke=col["head"], fc="white", fs=17, bold=True, arc=10)
        if i < len(stages) - 1:
            draw_arrow(ax, [(col_l + w_l / 2, sy + band_h),
                            (col_l + w_l / 2, sy + band_h + band_gap)],
                       color=col["stroke"], width=1.5)

        # 中：内容块（多个小盒纵向）
        contents = st.get("content", [])
        mh = band_h / max(len(contents), 1)
        for j, c in enumerate(contents):
            draw_box(ax, col_m, sy + j * mh + 4, w_m, mh - 8, c,
                     fill=col["fill"], stroke=col["stroke"], fs=15, arc=6)

        # 右：方法清单（一个盒，多行）
        methods = "\n".join(st.get("methods", []))
        draw_box(ax, col_r, sy, w_r, band_h, methods, fill=GROUP["fill"],
                 stroke=GROUP["stroke"], fs=14, fc=MUTED, arc=6)

        # 左→中、中→右 连接
        mid_y = sy + band_h / 2
        draw_arrow(ax, [(col_l + w_l, mid_y), (col_m - 8, mid_y)], color=MUTED, width=1.2)
        draw_arrow(ax, [(col_m + w_m, mid_y), (col_r - 8, mid_y)], color=MUTED, width=1.2)

    return _finish(fig, save_path)


# ============================================================================
# 模板 3：三栏阶段流程图
# ============================================================================

def diagram_stageflow(content: dict, save_path: str = "stageflow.png") -> str:
    """三栏阶段流程图（实色标题条 + 步骤流）。

    content 结构：
        {
            "title": "执行流程",
            "stages": [
                {"head": "阶段一", "steps": ["步骤1", "步骤2", "步骤3"]},
                ...   # 3 个阶段
            ]
        }
    """
    stages = content.get("stages", [])
    if len(stages) != 3:
        raise ValueError(f"stageflow 需要 3 个阶段，实际 {len(stages)} 个")

    W, H = 1000, 720
    fig, ax = setup_canvas(W, H)

    title = content.get("title")
    if title:
        draw_text(ax, W / 2, 40, 0, 0, title, fs=26, fc=INK, bold=True)

    col_gap = 30
    col_w = (W - 2 * 60 - 2 * col_gap) / 3
    cols = [60 + i * (col_w + col_gap) for i in range(3)]
    y0 = 90
    body_h = H - y0 - 40

    for i, st in enumerate(stages):
        col = STAGE_COLORS[i % len(STAGE_COLORS)]
        x = cols[i]
        steps = st.get("steps", [])
        if not steps:
            raise ValueError(f"stage {i + 1}.steps 不能为空")

        # 标题条
        draw_box(ax, x, y0, col_w, 56, st.get("head", f"阶段 {i + 1}"),
                 fill=col["head"], stroke=col["head"], fc="white", fs=18, bold=True, arc=0)

        # 步骤块（纵向，箭头串联）
        step_h = min(92, (body_h - 56 - (len(steps) - 1) * 26) / len(steps))
        sy = y0 + 56
        for j, s in enumerate(steps):
            draw_box(ax, x, sy, col_w, step_h, s, fill=col["fill"], stroke=col["stroke"],
                     fs=15, arc=8)
            if j < len(steps) - 1:
                draw_arrow(ax, [(x + col_w / 2, sy + step_h),
                                (x + col_w / 2, sy + step_h + 26)], color=col["stroke"], width=1.4)
            sy += step_h + 26

    # 栏间箭头（标题条下方，横向）
    for i in range(2):
        x = cols[i]
        draw_arrow(ax, [(x + col_w, y0 + 28), (x + col_w + col_gap, y0 + 28)],
                   color=MUTED, width=1.4)

    return _finish(fig, save_path)


# ============================================================================
# 模板 4：横版任务流水线图
# ============================================================================

def diagram_taskflow(content: dict, save_path: str = "taskflow.png") -> str:
    """横版任务流水线图（16:9，1360×765）。

    content 结构：
        {
            "title": "课题任务拆解",
            "tasks": [
                {"head": "任务一：数据预处理", "steps": ["清洗", "特征", "切分"]},
                ...   # 2~4 个任务
            ]
        }
    """
    tasks = content.get("tasks", [])
    if not 2 <= len(tasks) <= 4:
        raise ValueError(f"taskflow 需要 2~4 个任务，实际 {len(tasks)} 个")

    W, H = 1360, 765
    fig, ax = setup_canvas(W, H)

    title = content.get("title")
    if title:
        draw_text(ax, W / 2, 44, 0, 0, title, fs=26, fc=INK, bold=True)

    n = len(tasks)
    gap = 30
    x0, x1 = 50, W - 50
    task_w = (x1 - x0 - (n - 1) * gap) / n
    y0 = 100
    body_h = H - y0 - 60

    for i, t in enumerate(tasks):
        col = STAGE_COLORS[i % len(STAGE_COLORS)]
        tx = x0 + i * (task_w + gap)
        steps = t.get("steps", [])
        if not steps:
            raise ValueError(f"task {i + 1}.steps 不能为空")

        # 任务标题
        draw_box(ax, tx, y0, task_w, 60, t.get("head", f"任务 {i + 1}"),
                 fill=col["head"], stroke=col["head"], fc="white", fs=17, bold=True, arc=0)

        # 步骤流水线（纵向）
        step_h = min(90, (body_h - 60 - (len(steps) - 1) * 22) / len(steps))
        sy = y0 + 60
        for j, s in enumerate(steps):
            draw_box(ax, tx, sy, task_w, step_h, s, fill=col["fill"], stroke=col["stroke"],
                     fs=15, arc=8)
            if j < len(steps) - 1:
                draw_arrow(ax, [(tx + task_w / 2, sy + step_h),
                                (tx + task_w / 2, sy + step_h + 22)], color=col["stroke"], width=1.4)
            sy += step_h + 22

        # 任务间箭头
        if i < n - 1:
            draw_arrow(ax, [(tx + task_w, y0 + 30),
                            (tx + task_w + gap, y0 + 30)], color=MUTED, width=1.4)

    return _finish(fig, save_path)


# ============================================================================
# 模板 5：问题分析流程图（总分布局）
# ============================================================================

def diagram_problem_flow(content: dict, save_path: str = "problem_flow.png") -> str:
    """问题分析流程图（顶层居中 → 并行分支 → 底层收拢 + 反馈虚线）。

    content 结构：
        {
            "title": "问题分析",
            "root": "总问题",
            "branches": ["问题一", "问题二", "问题三"],
            "bottom": "综合方案",
            "feedback": "反馈修正",   # 可选，从 bottom 回指 root 的虚线
        }
    """
    W, H = 920, 820
    fig, ax = setup_canvas(W, H)

    title = content.get("title")
    if title:
        draw_text(ax, W / 2, 44, 0, 0, title, fs=26, fc=INK, bold=True)

    root = content.get("root", "总问题")
    branches = content.get("branches", [])
    if not 2 <= len(branches) <= 4:
        raise ValueError(f"problem_flow.branches 需 2~4 项，实际 {len(branches)}")
    bottom = content.get("bottom", "综合方案")
    feedback = content.get("feedback")

    # 顶层：总问题（居中）
    root_w, root_h = 360, 70
    rx, ry = W / 2 - root_w / 2, 90
    draw_hexagon(ax, rx, ry, root_w, root_h, root, fill=BAND["fill"], stroke=BAND["stroke"],
                 fs=19, fc=INK)

    # 中层：并行分支
    branch_w, branch_h = 240, 90
    by = 300
    xs = slots(60, W - 60, len(branches), gap=30)
    bx_centers = []
    for i, (x, b) in enumerate(zip(xs, branches)):
        col = STAGE_COLORS[i % len(STAGE_COLORS)]
        draw_box(ax, x, by, branch_w, branch_h, b, fill=col["fill"], stroke=col["stroke"],
                 fs=16, arc=10)
        bx_centers.append(x + branch_w / 2)

    # 顶层 → 各分支（正交：竖母线 + 横分支）
    bus_y = 230
    root_cx = W / 2
    draw_arrow(ax, [(root_cx, ry + root_h), (root_cx, bus_y)], color=MUTED, width=1.4)
    if len(bx_centers) > 1:
        ax.plot([bx_centers[0], bx_centers[-1]], [bus_y, bus_y], color=MUTED,
                linewidth=1.4, zorder=2)
    for cx in bx_centers:
        draw_arrow(ax, [(cx, bus_y), (cx, by)], color=MUTED, width=1.4)

    # 底层：综合方案（收拢）
    bot_w, bot_h = 360, 70
    botx, boty = W / 2 - bot_w / 2, 620
    draw_box(ax, botx, boty, bot_w, bot_h, bottom, fill=BAND["head"], stroke=BAND["head"],
             fc="white", fs=19, bold=True, arc=10)
    for cx in bx_centers:
        draw_arrow(ax, [(cx, by + branch_h), (cx, 540), (botx + bot_w / 2, 540),
                        (botx + bot_w / 2, boty)], color=MUTED, width=1.3)

    # 反馈虚线（从 bottom 回指 root）
    if feedback:
        draw_arrow(ax, [(botx + bot_w / 2, boty + bot_h), (W - 40, boty + bot_h),
                        (W - 40, ry + root_h / 2), (rx + root_w, ry + root_h / 2)],
                   color=FEEDBACK, width=1.4, linestyle=DASH)
        draw_text(ax, W - 40, (boty + bot_h + ry + root_h / 2) / 2, 0, 0, feedback,
                  fs=14, fc=FEEDBACK, ha="left")

    return _finish(fig, save_path)


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    import tempfile

    out = tempfile.mkdtemp(prefix="diagram_test_")
    print(f"框架图输出目录: {out}\n")

    roadmap = {
        "title": "城市交通拥堵治理研究技术路线",
        "bands": [
            {"head": "提出问题", "items": ["拥堵现状分析", "问题界定与假设", "数据采集"]},
            {"head": "数据与指标", "items": ["数据清洗", "指标体系构建", "缺失值处理"]},
            {"head": "方法与机制", "items": ["交通流模型", "GM(1,1) 预测", "优化模型"]},
            {"head": "结果对比", "items": ["模型验证", "方案对比", "误差分析"]},
            {"head": "评价推广", "items": ["方案评价", "灵敏度分析", "结论建议"]},
        ],
    }
    framework = {
        "title": "研究框架",
        "stages": [
            {"head": "数据准备", "content": ["数据采集", "数据清洗", "特征构造"], "methods": ["描述统计", "缺失值处理"]},
            {"head": "模型构建", "content": ["预测模型", "优化模型"], "methods": ["GM(1,1)", "遗传算法"]},
            {"head": "结果分析", "content": ["模型验证", "方案对比"], "methods": ["交叉验证", "误差分析"]},
        ],
    }
    stageflow = {
        "title": "执行流程",
        "stages": [
            {"head": "阶段一", "steps": ["数据预处理", "指标构建", "权重确定"]},
            {"head": "阶段二", "steps": ["模型求解", "参数寻优", "结果输出"]},
            {"head": "阶段三", "steps": ["结果验证", "敏感性分析", "方案评价"]},
        ],
    }
    taskflow = {
        "title": "课题任务拆解",
        "tasks": [
            {"head": "任务一：预处理", "steps": ["清洗", "特征", "切分"]},
            {"head": "任务二：建模", "steps": ["选模型", "训练", "调参"]},
            {"head": "任务三：求解", "steps": ["寻优", "对比", "输出"]},
            {"head": "任务四：评价", "steps": ["验证", "敏感性", "结论"]},
        ],
    }
    problem_flow = {
        "title": "问题分析",
        "root": "城市交通拥堵治理",
        "branches": ["问题一：交通流预测", "问题二：最优信号配时", "问题三：方案评价"],
        "bottom": "综合解决方案",
        "feedback": "反馈修正",
    }

    cases = [
        ("roadmap", diagram_roadmap, roadmap),
        ("framework", diagram_framework, framework),
        ("stageflow", diagram_stageflow, stageflow),
        ("taskflow", diagram_taskflow, taskflow),
        ("problem_flow", diagram_problem_flow, problem_flow),
    ]

    saved = []
    for name, fn, c in cases:
        try:
            p = fn(c, save_path=os.path.join(out, f"{name}.png"))
            saved.append(p)
            print(f"  [OK] {name} -> {p}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")

    print("-" * 50)
    print(f"共渲染 {len(saved)}/5 张框架图。输出目录: {out}")
