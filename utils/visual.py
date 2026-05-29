"""
图表绘制模块 — visual.py
=========================
可直接调用的论文级图表函数集合。
自动适配中文字体，高清 300 dpi 保存，默认关闭图形界面。
"""

import warnings
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


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
# 1. 折线图
# ============================================================================

def line_chart(
    x: Union[List, np.ndarray],
    y: Union[List, np.ndarray],
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    save_path: str = "line.png",
    color: str = "#2878B5",
    linewidth: float = 1.5,
    marker: str = "o",
    markersize: float = 4,
) -> str:
    """
    折线图。

    Parameters
    ----------
    x, y : array-like
        x 轴和 y 轴数据。
    xlabel, ylabel, title : str
        轴标签和标题。
    save_path : str
        保存路径。
    color : str
        线条颜色。
    linewidth, marker, markersize : 样式参数。

    Returns
    -------
    save_path : str
        图表保存路径。

    Examples
    --------
    >>> line_chart([1, 2, 3], [4, 5, 6], xlabel="时间", ylabel="值", title="折线图")
    """
    x = np.asarray(x); y = np.asarray(y)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x, y, color=color, linewidth=linewidth, marker=marker, markersize=markersize)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
) -> str:
    """
    多条折线图，自动生成图例。

    Parameters
    ----------
    x : array-like
        共享的 x 轴数据。
    y_dict : dict of {标签: y值数组}
        各条线的标签和数据。
    xlabel, ylabel, title : str
        轴标签和标题。
    save_path : str
        保存路径。

    Returns
    -------
    save_path : str

    Examples
    --------
    >>> multi_line_chart([1,2,3], {"A": [1,4,9], "B": [2,5,8]}, title="多折线")
    """
    x = np.asarray(x)
    n = len(y_dict)
    colors = plt.cm.tab10(np.linspace(0, 1, max(n, 10)))

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, (label, y) in enumerate(y_dict.items()):
        ax.plot(x, np.asarray(y), color=colors[i], linewidth=1.5,
                marker="o", markersize=3, label=label)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
    color: str = "#2878B5",
) -> str:
    """
    柱状图。

    Parameters
    ----------
    labels : list of str
        各柱标签。
    values : array-like
        各柱高度。
    xlabel, ylabel, title : str
        轴标签和标题。
    save_path : str
    color : str

    Returns
    -------
    save_path : str

    Examples
    --------
    >>> bar_chart(["A", "B", "C"], [10, 20, 15], title="柱状图")
    """
    values = np.asarray(values)
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(range(len(labels)), values, color=color, alpha=0.85, edgecolor="white")
    # 在柱顶标注数值
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                f"{v:.4g}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
) -> str:
    """
    分组柱状图。

    Parameters
    ----------
    labels : list of str
        各组标签（x 轴）。
    values_dict : dict of {组内标签: 值数组}
        每组内的柱形数据。
    xlabel, ylabel, title : str
    save_path : str

    Returns
    -------
    save_path : str

    Examples
    --------
    >>> grouped_bar_chart(["A","B"], {"甲": [1,2], "乙": [3,1]}, title="分组柱状图")
    """
    group_names = list(values_dict.keys())
    n_groups = len(group_names)
    n_items = len(labels)
    x = np.arange(n_items)
    total_width = 0.8
    bar_width = total_width / n_groups
    colors = plt.cm.Set2(np.linspace(0, 1, n_groups))

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, (gname, vals) in enumerate(values_dict.items()):
        offset = (i - n_groups / 2 + 0.5) * bar_width
        bars = ax.bar(x + offset, np.asarray(vals), bar_width,
                      color=colors[i], alpha=0.85, edgecolor="white", label=gname)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h, f"{h:.4g}",
                        ha="center", va="bottom", fontsize=6)

    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.legend(fontsize=8); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
) -> str:
    """
    散点图（可选颜色映射）。

    Parameters
    ----------
    x, y : array-like
        散点坐标。
    c : array-like, optional
        颜色映射值，None 则使用单一颜色。
    cmap : str
        colormap 名称。
    xlabel, ylabel, title : str
    save_path : str

    Returns
    -------
    save_path : str

    Examples
    --------
    >>> scatter_plot([1,2,3], [4,5,6], c=[0.1, 0.5, 0.9], title="散点图")
    """
    x = np.asarray(x); y = np.asarray(y)
    fig, ax = plt.subplots(figsize=(8, 5))
    sc = ax.scatter(x, y, c=c, cmap=cmap, alpha=0.7, edgecolors="grey", linewidths=0.3, s=40)
    if c is not None:
        plt.colorbar(sc, ax=ax, shrink=0.8)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
    figsize: tuple = (9, 7),
    fmt: str = ".2f",
    vmin: float = -1,
    vmax: float = 1,
) -> str:
    """
    矩阵热力图（使用 seaborn）。

    Parameters
    ----------
    data : pd.DataFrame or np.ndarray
        二维数据矩阵。若为 ndarray 则自动包裹为 DataFrame。
    title : str
    save_path : str
    annot : bool
        是否在格子内标注数值。
    cmap : str
        颜色映射。
    figsize : tuple
    fmt : str
        数值格式化字符串。
    vmin, vmax : float
        颜色映射范围。

    Returns
    -------
    save_path : str

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"A": [1,0.5], "B": [0.5,1]}, index=["X","Y"])
    >>> heatmap(df, title="相关系数")
    """
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
        ax.set_title(title, fontsize=13)
    except ImportError:
        # 回退纯 matplotlib
        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(data.values, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
        if annot:
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    val = data.values[i, j]
                    text_color = "white" if abs(val) > (vmax + vmin) / 2 else "black"
                    ax.text(j, i, format(val, fmt), ha="center", va="center",
                            fontsize=8, color=text_color)
        ax.set_xticks(range(data.shape[1]))
        ax.set_xticklabels(data.columns, rotation=45, ha="right", fontsize=9)
        ax.set_yticks(range(data.shape[0]))
        ax.set_yticklabels(data.index, fontsize=9)
        ax.set_title(title, fontsize=13)
        plt.colorbar(im, ax=ax, shrink=0.8)

    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
    color: str = "#2878B5",
    fill_alpha: float = 0.2,
) -> str:
    """
    雷达图。

    Parameters
    ----------
    categories : list of str
        各维度的名称（闭合多边形顶点）。
    values : array-like
        各维度的取值（与 categories 等长）。
    title : str
    save_path : str
    color : str
    fill_alpha : float
        填充透明度。

    Returns
    -------
    save_path : str

    Examples
    --------
    >>> radar_chart(["速度","力量","耐力"], [0.8, 0.6, 0.9], title="能力雷达图")
    """
    values = np.asarray(values, dtype=float)
    n = len(categories)

    # 计算角度（闭合）
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values = np.append(values, values[0])
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.fill(angles, values, color=color, alpha=fill_alpha)
    ax.plot(angles, values, color=color, linewidth=1.8, marker="o", markersize=5)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_ylim(0, max(values) * 1.15)
    ax.set_title(title, fontsize=13, pad=20)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
) -> str:
    """
    饼图（显示百分比）。

    Parameters
    ----------
    labels : list of str
        各类别名称。
    sizes : array-like
        各类别数值（自动归一化）。
    title : str
    save_path : str
    explode : list of float, optional
        突出偏移量，长度与 sizes 一致。

    Returns
    -------
    save_path : str

    Examples
    --------
    >>> pie_chart(["A", "B", "C"], [30, 45, 25], title="占比分布")
    """
    sizes = np.asarray(sizes, dtype=float)
    if explode is None:
        explode = [0.0] * len(sizes)

    colors = plt.cm.Set3(np.linspace(0, 1, len(sizes)))

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=90, pctdistance=0.6,
        textprops={"fontsize": 9},
    )
    # 百分比文字白色加粗
    for t in autotexts:
        t.set_color("white"); t.set_fontweight("bold")
    ax.set_title(title, fontsize=13)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
    color: str = "#2878B5",
) -> str:
    """
    直方图（可选密度曲线叠加）。

    Parameters
    ----------
    data : array-like
        原始数据。
    bins : int
        分箱数。
    xlabel, ylabel, title : str
    save_path : str
    density : bool
        若 True，以概率密度显示并叠加 KDE 曲线。
    color : str

    Returns
    -------
    save_path : str

    Examples
    --------
    >>> import numpy as np
    >>> histogram(np.random.randn(500), bins=30, title="正态分布直方图", density=True)
    """
    data = np.asarray(data).ravel()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(data, bins=bins, density=density, color=color, alpha=0.75,
            edgecolor="white", linewidth=0.5)
    if density:
        from scipy.stats import gaussian_kde
        kde = gaussian_kde(data)
        x_kde = np.linspace(data.min(), data.max(), 200)
        ax.plot(x_kde, kde(x_kde), color="darkred", linewidth=2, label="KDE 估计")
        ax.legend(fontsize=9)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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
) -> str:
    """
    正态概率 QQ 图。

    评估数据是否符合指定理论分布（默认正态）。

    Parameters
    ----------
    data : array-like
        样本数据。
    title : str
    save_path : str
    dist : str
        理论分布名称，默认 "norm"（正态分布）。

    Returns
    -------
    save_path : str

    Notes
    -----
    - 需要 scipy.stats。
    - 若数据符合正态，散点应近似沿对角线分布。

    Examples
    --------
    >>> import numpy as np
    >>> qq_plot(np.random.randn(100), title="正态性检验")
    """
    from scipy import stats as scipy_stats

    data = np.asarray(data).ravel()
    data = data[~np.isnan(data)]

    fig, ax = plt.subplots(figsize=(7, 7))
    res = scipy_stats.probplot(data, dist=dist, plot=ax)
    ax.set_title(title, fontsize=13)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _ensure_dir(save_path)
    fig.savefig(save_path, dpi=300, bbox_inches="tight")
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

    print("-" * 40)
    print(f"共生成 {len(saved)} 张图表:")
    for i, p in enumerate(saved, 1):
        print(f"  {i:2d}. {p}")
    print("-" * 40)
    print(f"所有图表已保存至: {out}")
