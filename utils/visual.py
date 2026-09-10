"""
图表绘制模块 — visual.py
=========================
可直接调用的论文级图表函数集合。
自动适配中文字体，出版级样式，高清 PNG+SVG 双格式保存。
"""

import warnings
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


# ============================================================================
# 色盲友好调色板
# ============================================================================

COLORBLIND_PALETTES = {
    "wang":        ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7",
                    "#56B4E9", "#F0E442", "#000000"],
    "tol_bright":  ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE",
                    "#AA3377", "#BBBBBB"],
    "tol_muted":   ["#332288", "#88CCEE", "#44AA99", "#117733", "#DDCC77",
                    "#CC6677", "#AA4499", "#882255"],
    "ibm":         ["#648FFF", "#785EF0", "#DC267F", "#FE6100", "#FFB000"],
}

DEFAULT_PALETTE = "wang"

# 标准图宽（英寸）
WIDTHS_IN = {"single": 3.5, "double": 7.2, "report": 6.3}

# 默认导出格式；渲染器（render_template.py）会临时置为 ("png", "svg", "pdf") 以追加 PDF
SAVE_FORMATS = ("png", "svg")


# ============================================================================
# 全局设置
# ============================================================================

_FONT_CANDIDATES = ["SimHei", "Songti SC", "WenQuanYi Micro Hei", "Microsoft YaHei", "DejaVu Sans"]

for _font in _FONT_CANDIDATES:
    try:
        plt.rcParams["font.sans-serif"] = [_font] + plt.rcParams["font.sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False
        break
    except Exception:
        continue

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")


def _ensure_dir(path: str) -> str:
    """确保保存路径的父目录存在。"""
    import os
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    return path


# ============================================================================
# 出版级样式设置（命名预设）
# ============================================================================

# 各命名样式在「基准出版样式」之上的差异。基准 = nature（当前默认，向后兼容）。
# 注意：science/ieee 通过 font.serif 末尾挂载中文字体，保证 CJK 文本回落不出现豆腐块。
STYLES = {
    "nature": {
        # 默认：无衬线、小字、细脊线、无网格 —— 与历史 apply_publication_style() 行为一致
        "font.family": "sans-serif",
        "font.size": 7.5,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
    },
    "science": {
        # 衬线（STIX/Times），略大字号，期刊单栏常见
        "font.family": "serif",
        "font.serif": ["STIXGeneral", "Times New Roman", "DejaVu Serif",
                       "SimHei", "Microsoft YaHei"],
        "font.size": 8.0,
        "axes.labelsize": 8.5,
        "axes.titlesize": 9.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
    },
    "ieee": {
        # IEEE 双栏紧凑：更小字号、刻度朝内
        "font.family": "sans-serif",
        "font.size": 6.5,
        "axes.labelsize": 7,
        "axes.titlesize": 8,
        "xtick.labelsize": 6,
        "ytick.labelsize": 6,
        "legend.fontsize": 6,
        "xtick.direction": "in",
        "ytick.direction": "in",
    },
    "plain": {
        # 极简：仅白底 + 去上右脊线，其余用 matplotlib 默认
    },
}

# 所有样式共用的基准（分辨率、导出、脊线、网格、白底）
_BASE_STYLE = {
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "svg.fonttype": "none",          # 文本导出为路径，保持字体一致
    "pdf.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "grid.alpha": 0,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
}


def apply_publication_style(style: str = "nature"):
    """设置出版级 matplotlib 全局参数，支持命名预设。

    预设：nature（默认，无衬线）/ science（衬线 STIX）/ ieee（双栏紧凑）/ plain（极简）。
    与旧版无参调用完全兼容；用 list_styles() 查看全部预设名。

    Parameters
    ----------
    style : str
        样式预设名，默认 "nature"。
    """
    if style not in STYLES:
        raise KeyError(f"未知样式 '{style}'，可用预设: {list(STYLES)}")
    plt.rcParams.update(_BASE_STYLE)
    plt.rcParams.update(STYLES[style])


def list_styles() -> list:
    """返回全部可用命名样式名。"""
    return list(STYLES)


def get_color_palette(n_colors: int = 8, palette: str = None) -> list:
    """获取色盲友好调色板的颜色列表。

    Parameters
    ----------
    n_colors : int
        需要的颜色数量。
    palette : str
        调色板名称（wang/tol_bright/tol_muted/ibm），默认 "wang"。

    Returns
    -------
    list of hex color strings
    """
    name = palette or DEFAULT_PALETTE
    colors = COLORBLIND_PALETTES.get(name, COLORBLIND_PALETTES[DEFAULT_PALETTE])
    if n_colors <= len(colors):
        return colors[:n_colors]
    # 循环重复
    return (colors * (n_colors // len(colors) + 1))[:n_colors]


# ============================================================================
# 统一保存（PNG + SVG 双格式，含灰阶预览）
# ============================================================================

def _save_figure(fig: plt.Figure, save_path: str, dpi: int = 300) -> str:
    """统一保存图表为多种格式（默认 PNG + SVG，可按需追加 PDF）。

    导出格式由模块级常量 ``SAVE_FORMATS`` 控制；调用方可在调用前临时修改
    该常量来追加格式（例如渲染器临时置为 ("png", "svg", "pdf")）。

    Parameters
    ----------
    fig : matplotlib Figure
    save_path : str
        PNG 文件路径（其余格式自动同目录同名）
    dpi : int
        分辨率，默认 300。

    Returns
    -------
    save_path : str
    """
    import os
    png_path = _ensure_dir(save_path)
    base, _ = os.path.splitext(png_path)

    for fmt in SAVE_FORMATS:
        out_path = png_path if fmt == "png" else f"{base}.{fmt}"
        fig.savefig(out_path, dpi=dpi, bbox_inches="tight")

    return png_path


def grayscale_preview(save_path: str) -> str:
    """为已保存的 PNG 生成灰阶预览版本，存入同目录 _qa/ 子目录。

    Parameters
    ----------
    save_path : str
        原始 PNG 文件路径。

    Returns
    -------
    preview_path : str
    """
    import os
    from PIL import Image
    qa_dir = os.path.join(os.path.dirname(os.path.abspath(save_path)), "_qa")
    os.makedirs(qa_dir, exist_ok=True)
    fname = os.path.basename(save_path)
    preview_path = os.path.join(qa_dir, f"gray_{fname}")

    img = Image.open(save_path).convert("L")
    img.save(preview_path)
    return preview_path


# ============================================================================
# 1. 折线图
# ============================================================================

def line_chart(
    x: Union[List, np.ndarray],
    y: Union[List, np.ndarray],
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    save_path: str = "line.png",
    color: str = None,
    linewidth: float = 1.5,
    marker: str = "o",
    markersize: float = 4,
    publication_style: bool = True,
) -> str:
    """折线图。"""
    if publication_style:
        apply_publication_style()
    if color is None:
        color = get_color_palette(1)[0]

    x = np.asarray(x); y = np.asarray(y)
    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    ax.plot(x, y, color=color, linewidth=linewidth, marker=marker, markersize=markersize)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 2. 多折线图
# ============================================================================

def multi_line_chart(
    x: Union[List, np.ndarray],
    y_dict: Dict[str, Union[List, np.ndarray]],
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    save_path: str = "multi_line.png",
    publication_style: bool = True,
) -> str:
    """多条折线图，自动生成图例。"""
    if publication_style:
        apply_publication_style()

    x = np.asarray(x)
    n = len(y_dict)
    colors = get_color_palette(n)

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    for i, (label, y) in enumerate(y_dict.items()):
        ax.plot(x, np.asarray(y), color=colors[i], linewidth=1.5,
                marker="o", markersize=3, label=label)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 3. 柱状图
# ============================================================================

def bar_chart(
    labels: List[str],
    values: Union[List, np.ndarray],
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    save_path: str = "bar.png",
    color: str = None,
    publication_style: bool = True,
) -> str:
    """柱状图。"""
    if publication_style:
        apply_publication_style()
    if color is None:
        color = get_color_palette(1)[0]

    values = np.asarray(values)
    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    bars = ax.bar(range(len(labels)), values, color=color, alpha=0.85, edgecolor="white", linewidth=0.3)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                f"{v:.4g}", ha="center", va="bottom", fontsize=6)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 4. 分组柱状图
# ============================================================================

def grouped_bar_chart(
    labels: List[str],
    values_dict: Dict[str, Union[List, np.ndarray]],
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    save_path: str = "grouped_bar.png",
    publication_style: bool = True,
) -> str:
    """分组柱状图。"""
    if publication_style:
        apply_publication_style()

    group_names = list(values_dict.keys())
    n_groups = len(group_names)
    n_items = len(labels)
    x = np.arange(n_items)
    total_width = 0.8
    bar_width = total_width / n_groups
    colors = get_color_palette(n_groups)

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    for i, (gname, vals) in enumerate(values_dict.items()):
        offset = (i - n_groups / 2 + 0.5) * bar_width
        bars = ax.bar(x + offset, np.asarray(vals), bar_width,
                      color=colors[i], alpha=0.85, edgecolor="white", linewidth=0.3, label=gname)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h, f"{h:.4g}",
                        ha="center", va="bottom", fontsize=5)

    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 5. 散点图
# ============================================================================

def scatter_plot(
    x: Union[List, np.ndarray],
    y: Union[List, np.ndarray],
    c: Optional[Union[List, np.ndarray]] = None,
    cmap: str = "viridis",
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    save_path: str = "scatter.png",
    publication_style: bool = True,
) -> str:
    """散点图（可选颜色映射）。使用色盲安全 colormap viridis。"""
    if publication_style:
        apply_publication_style()

    x = np.asarray(x); y = np.asarray(y)
    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    sc = ax.scatter(x, y, c=c, cmap=cmap, alpha=0.6, edgecolors="none", s=36)
    if c is not None:
        plt.colorbar(sc, ax=ax, shrink=0.8)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 6. 热力图
# ============================================================================

def heatmap(
    data: Union[pd.DataFrame, np.ndarray],
    title: str = "",
    save_path: str = "heatmap.png",
    annot: bool = True,
    cmap: str = "RdBu_r",
    figsize: tuple = None,
    fmt: str = ".2f",
    vmin: float = -1,
    vmax: float = 1,
    publication_style: bool = True,
) -> str:
    """矩阵热力图（使用 seaborn）。"""
    if publication_style:
        apply_publication_style()
    if figsize is None:
        figsize = (WIDTHS_IN["double"] * 0.7, WIDTHS_IN["double"] * 0.55)

    if isinstance(data, np.ndarray):
        data = pd.DataFrame(data)
    elif not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)

    try:
        import seaborn as sns
        fig, ax = plt.subplots(figsize=figsize)
        sns.heatmap(data, annot=annot, fmt=fmt, cmap=cmap,
                    vmin=vmin, vmax=vmax, square=True,
                    linewidths=0.5, ax=ax, cbar_kws={"shrink": 0.8})
        ax.set_title(title, fontsize=10)
    except ImportError:
        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(data.values, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
        if annot:
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    val = data.values[i, j]
                    text_color = "white" if abs(val) > (vmax + vmin) / 2 else "black"
                    ax.text(j, i, format(val, fmt), ha="center", va="center",
                            fontsize=7, color=text_color)
        ax.set_xticks(range(data.shape[1]))
        ax.set_xticklabels(data.columns, rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(data.shape[0]))
        ax.set_yticklabels(data.index, fontsize=7)
        ax.set_title(title, fontsize=10)
        plt.colorbar(im, ax=ax, shrink=0.8)

    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 7. 雷达图
# ============================================================================

def radar_chart(
    categories: List[str],
    values: Union[List, np.ndarray],
    title: str = "",
    save_path: str = "radar.png",
    color: str = None,
    fill_alpha: float = 0.15,
    publication_style: bool = True,
) -> str:
    """雷达图。"""
    if publication_style:
        apply_publication_style()
    if color is None:
        color = get_color_palette(1)[0]

    values = np.asarray(values, dtype=float)
    n = len(categories)

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values = np.append(values, values[0])
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color=color, alpha=fill_alpha)
    ax.plot(angles, values, color=color, linewidth=1.5, marker="o", markersize=4)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=8)
    ax.set_ylim(0, max(values) * 1.15)
    ax.set_title(title, fontsize=10, pad=18)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 8. 饼图
# ============================================================================

def pie_chart(
    labels: List[str],
    sizes: Union[List, np.ndarray],
    title: str = "",
    save_path: str = "pie.png",
    explode: Optional[List[float]] = None,
    publication_style: bool = True,
) -> str:
    """饼图（显示百分比）。

    注意：数学建模竞赛中，饼图在多于 4 个类别时信息密度较低，建议优先考虑
    分组柱状图。仅在类别数 ≤4 且强调占比关系时使用。
    """
    if publication_style:
        apply_publication_style()

    sizes = np.asarray(sizes, dtype=float)
    if explode is None:
        explode = [0.0] * len(sizes)

    colors = get_color_palette(len(sizes))

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=90, pctdistance=0.6,
        textprops={"fontsize": 8},
    )
    for t in autotexts:
        t.set_color("white"); t.set_fontweight("bold")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 9. 直方图
# ============================================================================

def histogram(
    data: Union[List, np.ndarray],
    bins: int = 10,
    xlabel: str = "",
    ylabel: str = "频数",
    title: str = "",
    save_path: str = "hist.png",
    density: bool = False,
    color: str = None,
    publication_style: bool = True,
) -> str:
    """直方图（可选密度曲线叠加）。"""
    if publication_style:
        apply_publication_style()
    if color is None:
        color = get_color_palette(1)[0]

    data = np.asarray(data).ravel()
    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    ax.hist(data, bins=bins, density=density, color=color, alpha=0.75,
            edgecolor="white", linewidth=0.3)
    if density:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(data)
        x_kde = np.linspace(data.min(), data.max(), 200)
        ax.plot(x_kde, kde(x_kde), color=get_color_palette(2)[1], linewidth=1.5, label="KDE 估计")
        ax.legend(fontsize=7, frameon=False)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 10. QQ 图
# ============================================================================

def qq_plot(
    data: Union[List, np.ndarray],
    title: str = "QQ 图",
    save_path: str = "qq.png",
    dist: str = "norm",
    publication_style: bool = True,
) -> str:
    """正态概率 QQ 图。"""
    if publication_style:
        apply_publication_style()

    from scipy import stats as scipy_stats

    data = np.asarray(data).ravel()
    data = data[~np.isnan(data)]

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    res = scipy_stats.probplot(data, dist=dist, plot=ax)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 附加图表：置信区间折线图
# ============================================================================

def line_with_ci(
    x: Union[List, np.ndarray],
    y: Union[List, np.ndarray],
    ci_lower: Union[List, np.ndarray],
    ci_upper: Union[List, np.ndarray],
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    save_path: str = "line_ci.png",
    color: str = None,
    label: str = "",
    publication_style: bool = True,
) -> str:
    """带置信区间的折线图。"""
    if publication_style:
        apply_publication_style()
    if color is None:
        color = get_color_palette(1)[0]

    x = np.asarray(x); y = np.asarray(y)
    lower = np.asarray(ci_lower); upper = np.asarray(ci_upper)

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    ax.fill_between(x, lower, upper, alpha=0.2, color=color, linewidth=0)
    ax.plot(x, y, color=color, linewidth=1.5, marker="o", markersize=3, label=label or None)
    if label:
        ax.legend(fontsize=7, frameon=False)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 附加图表：双 Y 轴图
# ============================================================================

def dual_axis_chart(
    x: Union[List, np.ndarray],
    y1: Union[List, np.ndarray],
    y2: Union[List, np.ndarray],
    y1_label: str = "",
    y2_label: str = "",
    xlabel: str = "",
    title: str = "",
    save_path: str = "dual_axis.png",
    y1_color: str = None,
    y2_color: str = None,
    publication_style: bool = True,
) -> str:
    """双 Y 轴折线图。

    注意：双 Y 轴图容易造成误导。仅在两组数据量纲不同且需要展示相对趋势时使用。
    图中必须明确标注左右 Y 轴的含义。
    """
    if publication_style:
        apply_publication_style()

    colors = get_color_palette(2)
    y1_color = y1_color or colors[0]
    y2_color = y2_color or colors[1]

    x = np.asarray(x); y1 = np.asarray(y1); y2 = np.asarray(y2)

    fig, ax1 = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    ax1.plot(x, y1, color=y1_color, linewidth=1.5, marker="o", markersize=3)
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(y1_label, color=y1_color)
    ax1.tick_params(axis="y", colors=y1_color)

    ax2 = ax1.twinx()
    ax2.plot(x, y2, color=y2_color, linewidth=1.5, marker="s", markersize=3, linestyle="--")
    ax2.set_ylabel(y2_label, color=y2_color)
    ax2.tick_params(axis="y", colors=y2_color)

    ax1.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：迭代收敛曲线
# ============================================================================

def convergence_chart(
    history: Union[List, np.ndarray],
    xlabel: str = "迭代次数",
    ylabel: str = "目标函数值",
    title: str = "迭代收敛曲线",
    save_path: str = "convergence.png",
    color: str = None,
    highlight_best: bool = True,
    log_y: bool = False,
    publication_style: bool = True,
) -> str:
    """迭代收敛曲线（遗传算法 / 模拟退火等）。

    Parameters
    ----------
    history : list or np.ndarray
        每代（或每温度）最优值，来自 ``optimization.genetic_algorithm()['history']``
        或 ``optimization.simulated_annealing()['history']``。
    highlight_best : bool
        是否标注最优值与收敛位置。
    log_y : bool
        目标值跨度大时对 Y 轴取对数。
    """
    if publication_style:
        apply_publication_style()
    if color is None:
        color = get_color_palette(1)[0]

    history = np.asarray(history, dtype=float).ravel()
    if len(history) == 0:
        raise ValueError("history 不能为空。")
    gens = np.arange(1, len(history) + 1)

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    ax.plot(gens, history, color=color, linewidth=1.5, marker="o", markersize=2)
    if log_y:
        ax.set_yscale("log")

    if highlight_best:
        best_idx = int(np.argmin(history))
        best_val = history[best_idx]
        best_color = get_color_palette(2)[1]
        ax.scatter([best_idx + 1], [best_val], color=best_color, s=36, zorder=5,
                   label=f"最优值 {best_val:.4g}")
        ax.axhline(best_val, color=best_color, linestyle="--", linewidth=0.8, alpha=0.7)
        ax.legend(fontsize=7, frameon=False)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：预测 vs 实际
# ============================================================================

def prediction_vs_actual(
    actual: Union[List, np.ndarray],
    predicted: Union[List, np.ndarray],
    xlabel: str = "实际值",
    ylabel: str = "预测值",
    title: str = "预测 vs 实际",
    save_path: str = "pred_vs_actual.png",
    color: str = None,
    show_metrics: bool = True,
    publication_style: bool = True,
) -> str:
    """预测值与实际值散点 + 45° 参考线，检验预测模型拟合质量。

    点越贴近对角线越好。可选在图中标注 R² 与 RMSE（内联计算，不依赖 model_library）。
    """
    if publication_style:
        apply_publication_style()
    if color is None:
        color = get_color_palette(1)[0]

    actual = np.asarray(actual, dtype=float).ravel()
    predicted = np.asarray(predicted, dtype=float).ravel()
    if len(actual) != len(predicted):
        raise ValueError(f"长度不一致: actual={len(actual)}, predicted={len(predicted)}")

    ss_res = np.sum((actual - predicted) ** 2)
    ss_tot = np.sum((actual - actual.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 1e-10 else float("nan")
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))

    lo = min(actual.min(), predicted.min())
    hi = max(actual.max(), predicted.max())

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.7))
    ax.scatter(actual, predicted, color=color, alpha=0.6, s=30, edgecolors="none")
    ax.plot([lo, hi], [lo, hi], color="gray", linestyle="--", linewidth=1.0,
            label="45° 参考线")
    if show_metrics:
        ax.text(0.03, 0.97, f"$R^2$ = {r2:.4f}\nRMSE = {rmse:.4g}",
                transform=ax.transAxes, va="top", ha="left", fontsize=7,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.8", alpha=0.9))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：残差诊断面板
# ============================================================================

def residual_panel(
    fitted: Union[List, np.ndarray],
    residuals: Union[List, np.ndarray],
    title: str = "残差诊断面板",
    save_path: str = "residual_panel.png",
    publication_style: bool = True,
) -> str:
    """1×2 残差诊断面板：残差-拟合值散点 + 残差分布直方图（含 KDE）。

    用于回归模型残差的同方差性/独立性诊断：
    - 左图残差应围绕 0 随机分布（无漏斗形/弯曲 → 无系统性偏差）；
    - 右图残差应近似正态。
    入参可由 ``statistics.multiple_regression()['summary']`` 的 ``.fittedvalues`` / ``.resid`` 取得。
    """
    if publication_style:
        apply_publication_style()

    fitted = np.asarray(fitted, dtype=float).ravel()
    residuals = np.asarray(residuals, dtype=float).ravel()
    if len(fitted) != len(residuals):
        raise ValueError(f"长度不一致: fitted={len(fitted)}, residuals={len(residuals)}")
    colors = get_color_palette(2)

    fig, axes = plt.subplots(1, 2, figsize=(WIDTHS_IN["double"], WIDTHS_IN["double"] * 0.45))

    ax = axes[0]
    ax.scatter(fitted, residuals, color=colors[0], alpha=0.6, s=30, edgecolors="none")
    ax.axhline(0, color="gray", linestyle="--", linewidth=1.0)
    ax.set_xlabel("拟合值")
    ax.set_ylabel("残差")

    ax = axes[1]
    ax.hist(residuals, bins="auto", density=True, color=colors[0], alpha=0.6,
            edgecolor="white", linewidth=0.3)
    from scipy.stats import gaussian_kde
    kde = gaussian_kde(residuals)
    x_kde = np.linspace(residuals.min(), residuals.max(), 200)
    ax.plot(x_kde, kde(x_kde), color=colors[1], linewidth=1.5, label="KDE")
    ax.axvline(0, color="gray", linestyle="--", linewidth=1.0)
    ax.set_xlabel("残差")
    ax.set_ylabel("密度")
    ax.legend(fontsize=7, frameon=False)

    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：灵敏度龙卷风图
# ============================================================================

def tornado_chart(
    param_names: List[str],
    low_values: Union[List, np.ndarray],
    high_values: Union[List, np.ndarray],
    base_value: Union[float, List, np.ndarray] = None,
    xlabel: str = "目标函数值",
    title: str = "灵敏度龙卷风图",
    save_path: str = "tornado.png",
    publication_style: bool = True,
) -> str:
    """灵敏度龙卷风图：展示各参数在低/高取值下对目标的影响范围。

    按影响范围 |high - low| 降序排列，最敏感参数在最上方。
    适用于 SKILL.md 稳健性分析要求的「关键参数敏感性扫描」。

    Parameters
    ----------
    param_names : list of str
        参数名。
    low_values / high_values : list
        各参数在低/高取值下的目标函数值。
    base_value : float or list, optional
        基准取值（画一条基准竖线），默认取 low/high 均值。
    """
    if publication_style:
        apply_publication_style()

    n = len(param_names)
    low = np.asarray(low_values, dtype=float).ravel()
    high = np.asarray(high_values, dtype=float).ravel()
    if len(low) != n or len(high) != n:
        raise ValueError(f"参数数量不一致: names={n}, low={len(low)}, high={len(high)}")

    spread = np.abs(high - low)
    order = np.argsort(spread)[::-1]
    names_sorted = [param_names[i] for i in order]
    low_sorted = low[order]
    high_sorted = high[order]

    colors = get_color_palette(2)

    y = np.arange(n)[::-1]
    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.6))
    for i in range(n):
        ax.barh(y[i], high_sorted[i] - low_sorted[i], left=low_sorted[i], height=0.6,
                color=colors[0] if high_sorted[i] >= low_sorted[i] else colors[1],
                alpha=0.85, edgecolor="white", linewidth=0.3)

    if base_value is None:
        base_x = float(np.mean([low_sorted, high_sorted]))
    else:
        base_arr = np.asarray(base_value, dtype=float)
        base_x = float(base_arr) if base_arr.ndim == 0 else float(np.mean(base_arr.ravel()))
    ax.axvline(base_x, color="gray", linestyle="--", linewidth=1.0, label="基准值")

    ax.set_yticks(y)
    ax.set_yticklabels(names_sorted, fontsize=7)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：泰勒图
# ============================================================================

def taylor_diagram(
    std_ratio: Union[List, np.ndarray],
    correlation: Union[List, np.ndarray],
    labels: List[str] = None,
    rmsd: Union[List, np.ndarray] = None,
    title: str = "泰勒图",
    save_path: str = "taylor.png",
    publication_style: bool = True,
) -> str:
    """泰勒图（Taylor Diagram）：在极坐标下同时比较多个模型的三个统计量。

    径向距离 = 模型标准差 / 参考标准差（越接近 1 越好）；
    角度 = arccos(相关系数 R)（越接近 0° 即 R→1 越好）；
    与参考点 (1, 0) 的距离 = 归一化 RMS 误差（越近越好）。

    Parameters
    ----------
    std_ratio : list
        各模型的「标准差 / 参考标准差」比值。
    correlation : list
        各模型与参考序列的相关系数 R（∈[-1, 1]）。
    labels : list of str, optional
        各模型名称，用于图例。
    rmsd : list, optional
        各模型归一化 RMS 误差；缺省由 std_ratio 与 correlation 推导。
    """
    if publication_style:
        apply_publication_style()

    std_ratio = np.asarray(std_ratio, dtype=float).ravel()
    correlation = np.clip(np.asarray(correlation, dtype=float).ravel(), -1.0, 1.0)
    n = len(std_ratio)
    if n == 0:
        raise ValueError("std_ratio 与 correlation 不能为空。")
    if len(correlation) != n:
        raise ValueError(f"std_ratio({n}) 与 correlation({len(correlation)}) 长度不一致。")

    if rmsd is None:
        rmsd = np.sqrt(1 + std_ratio ** 2 - 2 * std_ratio * correlation)
    else:
        rmsd = np.asarray(rmsd, dtype=float).ravel()

    if labels is None:
        labels = [f"模型 {i+1}" for i in range(n)]
    else:
        labels = [str(lb) for lb in labels]

    colors = get_color_palette(n)

    theta = np.arccos(correlation)  # R -> 角度（弧度）
    r = std_ratio

    rmax = max(1.2, float(np.ceil(std_ratio.max() * 4) / 4) + 0.25)

    fig = plt.figure(figsize=(6.5, 6.0))
    ax = fig.add_subplot(111, polar=True)

    # 相关系数弧线（径向线，角度 = arccos(R)）
    for c in [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.99, 1.0]:
        for sign in (1, -1):
            ax.plot([0, sign * np.arccos(c)], [0, rmax], color="0.85",
                    linewidth=0.5, zorder=0)
    # 相关系数刻度：角度（度）与 R 值
    angle_ticks = [0, 30, 45, 60, 90]
    corr_labels = ["1", "0.87", "0.71", "0.5", "0"]
    ax.set_thetagrids(angle_ticks, labels=corr_labels, fontsize=6)

    # 标准差同心圆
    std_ticks = np.arange(0.25, rmax + 1e-9, 0.25)
    ax.set_yticks(std_ticks)
    ax.set_yticklabels([f"{t:.2f}" for t in std_ticks], fontsize=6, color="0.4")
    ax.set_ylim(0, rmax)

    # RMSE 同心圆弧（圆心在参考点 (1, 0)，半径 = 归一化 RMS）
    for e in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
        phi = np.linspace(0, 2 * np.pi, 360)
        x = 1 + e * np.cos(phi)
        y = e * np.sin(phi)
        rr = np.sqrt(x ** 2 + y ** 2)
        tt = np.arctan2(y, x)
        mask = rr <= rmax
        if mask.any():
            ax.plot(tt[mask], rr[mask], color="0.8", linewidth=0.5, zorder=0)

    # 参考点
    ax.plot([0], [1.0], marker="o", color="black", markersize=6, label="参考", zorder=5)

    # 模型点
    for i in range(n):
        ax.plot([theta[i]], [r[i]], marker="o", color=colors[i], markersize=7, zorder=5,
                label=f"{labels[i]} (R={correlation[i]:.2f}, RMS={rmsd[i]:.2f})")

    ax.legend(fontsize=6, frameon=False, bbox_to_anchor=(1.18, 1.02), loc="upper right")
    ax.set_title(title, fontsize=10, pad=20)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：ROC 曲线
# ============================================================================

def roc_curve(
    y_true: Union[List, np.ndarray],
    y_score: Union[List, np.ndarray],
    n_folds: int = None,
    title: str = "ROC 曲线",
    save_path: str = "roc.png",
    publication_style: bool = True,
) -> str:
    """ROC 曲线 + AUC 标注，可选 K 折交叉验证均值±标准差。

    Parameters
    ----------
    y_true : list
        真实标签（0/1）。
    y_score : list
        预测得分（概率或决策值，越高越可能是正类）。
    n_folds : int, optional
        若指定 ≥2，用分层 K 折交叉验证，绘制各折 ROC 与均值 ROC（含阴影）。
    """
    if publication_style:
        apply_publication_style()

    try:
        from sklearn.metrics import roc_curve as _sk_roc, auc
    except ImportError:
        raise ImportError("ROC 曲线需要 scikit-learn。请运行: pip install scikit-learn")

    y_true = np.asarray(y_true, dtype=int).ravel()
    y_score = np.asarray(y_score, dtype=float).ravel()
    if len(y_true) != len(y_score):
        raise ValueError(f"长度不一致: y_true={len(y_true)}, y_score={len(y_score)}")

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.7))

    if n_folds and n_folds >= 2:
        from sklearn.model_selection import StratifiedKFold
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        tprs, aucs, mean_fpr = [], [], np.linspace(0, 1, 200)
        colors = get_color_palette(n_folds)
        for i, (tr, te) in enumerate(skf.split(y_score, y_true)):
            fpr, tpr, _ = _sk_roc(y_true[te], y_score[te])
            tprs.append(np.interp(mean_fpr, fpr, tpr))
            tprs[-1][0] = 0.0
            aucs.append(auc(fpr, tpr))
            ax.plot(fpr, tpr, color=colors[i], linewidth=0.7, alpha=0.5,
                    label=f"折 {i+1} (AUC={aucs[-1]:.3f})")
        mean_tpr = np.mean(tprs, axis=0)
        mean_tpr[-1] = 1.0
        std_tpr = np.std(tprs, axis=0)
        mean_auc = auc(mean_fpr, mean_tpr)
        ax.plot(mean_fpr, mean_tpr, color=get_color_palette(1)[0], linewidth=1.6,
                label=f"均值 (AUC={mean_auc:.3f} $\\pm$ {np.std(aucs):.3f})")
        ax.fill_between(mean_fpr, mean_tpr - std_tpr, mean_tpr + std_tpr,
                        color=get_color_palette(1)[0], alpha=0.15, linewidth=0)
    else:
        fpr, tpr, _ = _sk_roc(y_true, y_score)
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color=get_color_palette(1)[0], linewidth=1.6,
                label=f"AUC = {roc_auc:.4f}")

    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", linewidth=1.0, label="随机猜测")
    ax.set_xlim([0, 1])
    ax.set_ylim([0, 1])
    ax.set_xlabel("假阳率 (FPR)")
    ax.set_ylabel("真阳率 (TPR)")
    ax.set_title(title)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：云雨图（raincloud）
# ============================================================================

def raincloud(
    data_dict: Dict[str, Union[List, np.ndarray]],
    xlabel: str = "",
    ylabel: str = "值",
    title: str = "云雨图",
    save_path: str = "raincloud.png",
    jitter: float = 0.08,
    publication_style: bool = True,
) -> str:
    """云雨图（raincloud）：半边小提琴（KDE）+ 抖动散点 + 箱线，比较多个分布形态。

    比传统箱线图展示更多信息（分布形状、离群点、集中趋势）。
    """
    if publication_style:
        apply_publication_style()

    labels = list(data_dict.keys())
    n = len(labels)
    colors = get_color_palette(n)
    rng = np.random.default_rng(42)

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.6))
    from scipy.stats import gaussian_kde

    for i, (label, raw) in enumerate(data_dict.items()):
        vals = np.asarray(raw, dtype=float)
        vals = vals[~np.isnan(vals)]
        if len(vals) == 0:
            continue
        x = i + 1  # 分组位置（1-based），小提琴画在左侧

        # 半边小提琴（KDE 向左延伸）
        kde = gaussian_kde(vals)
        grid = np.linspace(vals.min() - 1e-9, vals.max() + 1e-9, 200)
        dens = kde(grid)
        dens = dens / (dens.max() or 1.0) * 0.4
        ax.fill_betweenx(grid, x, x - dens, color=colors[i], alpha=0.55, linewidth=0)

        # 抖动散点（右侧）
        ax.scatter(x + rng.uniform(-jitter, jitter, len(vals)), vals,
                   color=colors[i], alpha=0.35, s=18, edgecolors="none")

        # 箱线（细，置于分组位置）
        ax.boxplot(vals, positions=[x], widths=0.18, showfliers=False, whis=1.5,
                   patch_artist=True,
                   boxprops=dict(facecolor="white", edgecolor=colors[i], linewidth=1.0),
                   whiskerprops=dict(color=colors[i], linewidth=1.0),
                   capprops=dict(color=colors[i], linewidth=1.0),
                   medianprops=dict(color=colors[i], linewidth=1.4))

    ax.set_xticks(range(1, n + 1))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：聚类散点图
# ============================================================================

def cluster_scatter(
    X_2d: Union[np.ndarray, List],
    labels: Union[List, np.ndarray],
    centers: Optional[np.ndarray] = None,
    hull: bool = True,
    title: str = "聚类散点图",
    xlabel: str = "维度 1",
    ylabel: str = "维度 2",
    save_path: str = "cluster_scatter.png",
    publication_style: bool = True,
) -> str:
    """聚类结果散点图（二维投影 + 簇质心 + 可选凸包）。

    入参 ``X_2d`` 通常取 ``pca_analysis()['scores'][:, :2]``，``labels`` 取
    ``kmeans_cluster()['labels']``。
    """
    if publication_style:
        apply_publication_style()

    X = np.asarray(X_2d, dtype=float)
    if X.ndim != 2 or X.shape[1] < 2:
        raise ValueError("X_2d 需为 (n, 2) 形状的二维投影。")
    labels = np.asarray(labels).ravel()
    n_clusters = int(labels.max()) + 1 if len(labels) else 0
    colors = get_color_palette(max(n_clusters, 1))

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.7))

    for k in range(n_clusters):
        mask = labels == k
        if not mask.any():
            continue
        ax.scatter(X[mask, 0], X[mask, 1], color=colors[k % len(colors)],
                   alpha=0.6, s=30, edgecolors="none", label=f"簇 {k+1}")

    if centers is not None:
        centers = np.asarray(centers, dtype=float)
        if centers.ndim == 2 and centers.shape[1] >= 2:
            ax.scatter(centers[:, 0], centers[:, 1], marker="*", s=200,
                       color="black", edgecolor="white", linewidth=0.5,
                       label="质心", zorder=5)

    if hull:
        from scipy.spatial import ConvexHull
        for k in range(n_clusters):
            pts = X[labels == k]
            if len(pts) >= 3:
                try:
                    h = ConvexHull(pts[:, :2])
                    for s in h.simplices:
                        ax.plot(pts[s, 0], pts[s, 1], color=colors[k % len(colors)],
                                linewidth=0.7, alpha=0.7)
                except Exception:
                    pass

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：层次聚类树状图
# ============================================================================

def dendrogram(
    Z: np.ndarray,
    labels: Optional[List] = None,
    title: str = "层次聚类树状图",
    xlabel: str = "样本",
    ylabel: str = "距离",
    save_path: str = "dendrogram.png",
    color_threshold: float = None,
    publication_style: bool = True,
) -> str:
    """层次聚类树状图。

    入参 ``Z`` 为 linkage 矩阵，取 ``hierarchical_cluster()['linkage_matrix']``。
    """
    if publication_style:
        apply_publication_style()

    from scipy.cluster.hierarchy import dendrogram as _scipy_dendrogram

    Z = np.asarray(Z, dtype=float)
    fig, ax = plt.subplots(figsize=(WIDTHS_IN["double"], WIDTHS_IN["double"] * 0.5))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _scipy_dendrogram(Z, ax=ax, labels=labels, leaf_rotation=90, leaf_font_size=6,
                          color_threshold=color_threshold)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 高级图表：肘部法则
# ============================================================================

def elbow_curve(
    inertias: Union[List, np.ndarray],
    k_values: Optional[List] = None,
    title: str = "肘部法则 (K-means 选 K)",
    xlabel: str = "聚类数 K",
    ylabel: str = "簇内平方和 (SSE)",
    save_path: str = "elbow.png",
    publication_style: bool = True,
) -> str:
    """肘部法则曲线：不同 K 下的簇内平方和，用于选择最佳聚类数。"""
    if publication_style:
        apply_publication_style()

    inertias = np.asarray(inertias, dtype=float).ravel()
    if k_values is None:
        k_values = list(range(1, len(inertias) + 1))
    else:
        k_values = list(k_values)

    fig, ax = plt.subplots(figsize=(WIDTHS_IN["report"], WIDTHS_IN["report"] * 0.55))
    ax.plot(k_values, inertias, color=get_color_palette(1)[0], linewidth=1.5,
            marker="o", markersize=4)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    _save_figure(fig, save_path)
    plt.close(fig)
    return save_path


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    import os
    import tempfile

    out = tempfile.mkdtemp(prefix="visual_test_")
    print(f"图表输出目录: {out}\n")
    print("色盲友好调色板:")
    for name, colors in COLORBLIND_PALETTES.items():
        print(f"  {name}: {colors[:4]}...")

    rng = np.random.default_rng(42)
    x = np.linspace(0, 4 * np.pi, 50)
    y1 = np.sin(x) + rng.normal(0, 0.1, len(x))
    y2 = np.cos(x) + rng.normal(0, 0.1, len(x))

    saved = []

    # 1. 折线图
    saved.append(line_chart(x, y1, xlabel="x", ylabel="sin(x)", title="折线图",
                            save_path=os.path.join(out, "line.png")))

    # 2. 多折线图
    saved.append(multi_line_chart(x, {"sin(x)": y1, "cos(x)": y2},
                                  xlabel="x", ylabel="值", title="多折线图",
                                  save_path=os.path.join(out, "multi_line.png")))

    # 3. 柱状图
    saved.append(bar_chart(["北京", "上海", "广州", "深圳", "杭州"],
                           [40000, 44000, 28000, 32000, 21000],
                           title="城市 GDP（亿元）",
                           save_path=os.path.join(out, "bar.png")))

    # 4. 分组柱状图
    saved.append(grouped_bar_chart(
        ["2020", "2021", "2022", "2023"],
        {"产品A": [120, 135, 148, 162], "产品B": [80, 95, 110, 130], "产品C": [45, 52, 60, 75]},
        xlabel="年份", ylabel="销售额（万元）", title="分类销售对比",
        save_path=os.path.join(out, "grouped_bar.png"),
    ))

    # 5. 散点图
    saved.append(scatter_plot(
        rng.normal(0, 1, 200), rng.normal(2, 1.5, 200),
        c=rng.random(200), cmap="viridis",
        xlabel="X", ylabel="Y", title="散点图（颜色映射）",
        save_path=os.path.join(out, "scatter.png"),
    ))

    # 6. 热力图
    corr_df = pd.DataFrame({
        "GDP": [1.0, 0.72, -0.35],
        "消费": [0.72, 1.0, -0.18],
        "失业率": [-0.35, -0.18, 1.0],
    }, index=["GDP", "消费", "失业率"])
    saved.append(heatmap(corr_df, title="经济指标相关系数",
                         save_path=os.path.join(out, "heatmap.png")))

    # 7. 雷达图
    saved.append(radar_chart(
        ["创新力", "成本控制", "交付速度", "产品质量", "客户满意度", "市场份额"],
        [0.85, 0.62, 0.91, 0.78, 0.88, 0.65],
        title="企业竞争力雷达图",
        save_path=os.path.join(out, "radar.png"),
    ))

    # 8. 饼图
    saved.append(pie_chart(
        ["制造业", "服务业", "房地产", "农业", "其他"],
        [35, 28, 18, 10, 9],
        title="产业结构占比 (%)",
        save_path=os.path.join(out, "pie.png"),
    ))

    # 9. 直方图
    saved.append(histogram(
        rng.normal(100, 15, 500),
        bins=30, xlabel="分数", ylabel="频数",
        title="考试成绩分布", density=True,
        save_path=os.path.join(out, "hist.png"),
    ))

    # 10. QQ 图
    saved.append(qq_plot(
        rng.normal(0, 1, 200),
        title="正态性 QQ 图",
        save_path=os.path.join(out, "qq.png"),
    ))

    # 11. 置信区间图
    saved.append(line_with_ci(
        x, y1,
        y1 - 0.15, y1 + 0.15,
        xlabel="x", ylabel="sin(x)", title="折线图（含 95% CI）",
        save_path=os.path.join(out, "line_ci.png"),
    ))

    # 12. 双Y轴图
    saved.append(dual_axis_chart(
        x, y1, y2 * 100,
        y1_label="sin(x)", y2_label="100×cos(x)",
        xlabel="x", title="双 Y 轴对比",
        save_path=os.path.join(out, "dual_axis.png"),
    ))

    # 13. 收敛曲线
    hist = np.minimum.accumulate(5 + rng.normal(0, 1, 80))
    saved.append(convergence_chart(hist, title="遗传算法收敛曲线",
                                   save_path=os.path.join(out, "convergence.png")))

    # 14. 预测 vs 实际
    actual = rng.normal(0, 1, 120)
    pred = actual + rng.normal(0, 0.3, 120)
    saved.append(prediction_vs_actual(actual, pred,
                                      save_path=os.path.join(out, "pred_vs_actual.png")))

    # 15. 残差面板
    fitted = np.linspace(0, 10, 120)
    resid = rng.normal(0, 1, 120)
    saved.append(residual_panel(fitted, resid,
                                save_path=os.path.join(out, "residual_panel.png")))

    # 16. 龙卷风图
    saved.append(tornado_chart(
        ["参数α", "参数β", "参数γ", "参数δ"],
        [10, 20, 5, 8], [14, 26, 9, 9],
        title="灵敏度龙卷风图",
        save_path=os.path.join(out, "tornado.png"),
    ))

    # 17. 泰勒图
    saved.append(taylor_diagram(
        [0.8, 1.1, 1.3], [0.95, 0.88, 0.75],
        labels=["模型A", "模型B", "模型C"],
        save_path=os.path.join(out, "taylor.png"),
    ))

    # 18. ROC 曲线
    y_true = rng.integers(0, 2, 200)
    y_score = np.clip(y_true * 0.8 + rng.normal(0.5, 0.25, 200), 0, 1)
    saved.append(roc_curve(y_true, y_score,
                           save_path=os.path.join(out, "roc.png")))

    # 19. 云雨图
    saved.append(raincloud(
        {"组1": rng.normal(0, 1, 200), "组2": rng.normal(1, 1.5, 200),
         "组3": rng.normal(2, 1, 150)},
        save_path=os.path.join(out, "raincloud.png"),
    ))

    # 20. 聚类散点
    X2d = rng.normal(0, 1, (120, 2))
    cl_labels = (X2d[:, 0] > 0).astype(int)
    saved.append(cluster_scatter(X2d, cl_labels,
                                 save_path=os.path.join(out, "cluster_scatter.png")))

    # 21. 层次聚类树状图
    from scipy.cluster.hierarchy import linkage
    Z = linkage(rng.normal(0, 1, (12, 2)), method="ward")
    saved.append(dendrogram(Z, save_path=os.path.join(out, "dendrogram.png")))

    # 22. 肘部法则
    saved.append(elbow_curve([100, 60, 40, 30, 25, 22],
                             save_path=os.path.join(out, "elbow.png")))

    print("-" * 40)
    print(f"共生成 {len(saved)} 张图表:")
    for i, p in enumerate(saved, 1):
        svg = p.replace(".png", ".svg")
        has_svg = "（+SVG）" if os.path.exists(svg) else ""
        print(f"  {i:2d}. {p} {has_svg}")
    print("-" * 40)
    print(f"所有图表已保存至: {out}")
