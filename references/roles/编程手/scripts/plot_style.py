#!/usr/bin/env python3
"""
出版级绘图样式模块 — plot_style.py
=====================================
出版级命名样式入口（委托 utils.visual.apply_publication_style，单一数据源），
可直接在代码中调用或作为命令行工具运行。

用法（Python）：
    from references.roles.编程手.scripts.plot_style import apply_style, get_palette
    apply_style()
    colors = get_palette(5)

用法（命令行）：
    python plot_style.py --check    # 检查样式是否可正确设置
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 单一数据源：样式预设统一来自 utils.visual，避免两处漂移
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils import visual

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


def apply_style(style: str = "nature"):
    """设置出版级 matplotlib 全局参数（委托 utils.visual，单一数据源）。

    预设：nature（默认）/ science / ieee / plain，见 list_styles()。
    """
    visual.apply_publication_style(style)


def list_styles() -> list:
    """返回全部可用命名样式名。"""
    return visual.list_styles()


if __name__ == "__main__":
    import sys
    # Windows 中文控制台默认 GBK，统一转 UTF-8 输出避免崩溃
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    if "--check" in sys.argv:
        try:
            # 遍历全部命名预设，确保都能正确应用
            for s in list_styles():
                apply_style(s)
            assert not plt.rcParams["axes.spines.top"], "spines.top 应为 False"
            assert not plt.rcParams["axes.spines.right"], "spines.right 应为 False"
            assert plt.rcParams["savefig.dpi"] == 300, "DPI 应为 300"
            print("PASS — 出版级样式设置成功")
            print(f"  预设: {list_styles()}")
            print(f"  调色板: {len(COLOR_SEQUENCE)} 种颜色")
            print(f"  图宽预设: {WIDTHS_IN}")
        except Exception as e:
            print(f"FAIL — {e}")
            sys.exit(1)
    else:
        apply_style()
        print("出版级样式已应用。可用预设：")
        for s in list_styles():
            print(f"  - {s}")
        print("可用调色板颜色：")
        for name, color in PALETTE.items():
            print(f"  {name:12s} {color}")
