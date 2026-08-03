#!/usr/bin/env python3
"""
出版级绘图样式模块 — plot_style.py
=====================================
提供 apply_publication_style() 的独立脚本版本，
可直接在代码中调用或作为命令行工具运行。

用法（Python）：
    from references.roles.编程手.scripts.plot_style import apply_style, get_palette
    apply_style()
    colors = get_palette(5)

用法（命令行）：
    python plot_style.py --check    # 检查样式是否可正确设置
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── 色盲友好调色板 ────────────────────────────────────────────

PALETTE = {
    "primary": "#0072B2",
    "secondary": "#E69F00",
    "positive": "#009E73",
    "contrast": "#D55E00",
    "accent": "#CC79A7",
    "sky": "#56B4E9",
    "neutral": "#6B7280",
    "dark": "#222222",
}

COLOR_SEQUENCE = [
    PALETTE["primary"],
    PALETTE["secondary"],
    PALETTE["positive"],
    PALETTE["contrast"],
    PALETTE["accent"],
    PALETTE["sky"],
    PALETTE["neutral"],
    PALETTE["dark"],
]

WIDTHS_IN = {"single": 3.5, "double": 7.2, "report": 6.3}


def get_palette(n_colors: int = 4) -> list:
    """返回 n 个色盲友好颜色。"""
    if n_colors <= len(COLOR_SEQUENCE):
        return COLOR_SEQUENCE[:n_colors]
    return (COLOR_SEQUENCE * (n_colors // len(COLOR_SEQUENCE) + 1))[:n_colors]


def apply_style():
    """设置出版级 matplotlib 全局参数。

    特性：
    - 白底，无上/右坐标轴脊线
    - 无网格
    - 7.5pt 字号
    - 300 DPI
    - SVG 文字导出为路径（保证字体可移植）
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
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        try:
            apply_style()
            # 验证几个关键参数
            assert not plt.rcParams["axes.spines.top"], "spines.top 应为 False"
            assert not plt.rcParams["axes.spines.right"], "spines.right 应为 False"
            assert plt.rcParams["savefig.dpi"] == 300, "DPI 应为 300"
            print("PASS — 出版级样式设置成功")
            print(f"  调色板: {len(COLOR_SEQUENCE)} 种颜色")
            print(f"  图宽预设: {WIDTHS_IN}")
        except Exception as e:
            print(f"FAIL — {e}")
            sys.exit(1)
    else:
        apply_style()
        print("出版级样式已应用。可用调色板颜色：")
        for name, color in PALETTE.items():
            print(f"  {name:12s} {color}")
