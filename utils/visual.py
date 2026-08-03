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
# 出版级样式设置
# ============================================================================

def apply_publication_style():
    """设置出版级（Nature/SCI 风格）matplotlib 全局参数。

    调用后所有后续图表自动采用：白底、无上右坐标轴脊线、无网格、
    7.5pt 字体、300 DPI、SVG 字体导出为路径。

    可在绘图前调用一次，或作为上下文管理器在特定图表中使用。
    """
    plt.rcParams.update({
        "font.size": 7.5,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
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
    })


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
    """统一保存图表为 PNG + SVG 双格式，可选择性生成灰阶预览。

    Parameters
    ----------
    fig : matplotlib Figure
    save_path : str
        PNG 文件路径（SVG 自动同目录同名）
    dpi : int
        分辨率，默认 300。

    Returns
    -------
    save_path : str
    """
    import os
    png_path = _ensure_dir(save_path)
    base, _ = os.path.splitext(png_path)
    svg_path = base + ".svg"

    fig.savefig(png_path, dpi=dpi, bbox_inches="tight")
    fig.savefig(svg_path, dpi=dpi, bbox_inches="tight")

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

    print("-" * 40)
    print(f"共生成 {len(saved)} 张图表:")
    for i, p in enumerate(saved, 1):
        svg = p.replace(".png", ".svg")
        has_svg = "（+SVG）" if os.path.exists(svg) else ""
        print(f"  {i:2d}. {p} {has_svg}")
    print("-" * 40)
    print(f"所有图表已保存至: {out}")
