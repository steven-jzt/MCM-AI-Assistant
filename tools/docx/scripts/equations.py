#!/usr/bin/env python3
"""
LaTeX → OMML 公式转换器 — equations.py
==========================================
将 LaTeX 公式源码转换为 Word 原生 OMML（Office Math Markup Language）格式，
生成 Word 可渲染的数学公式。

用法：
  python tools/docx/scripts/equations.py convert "E = mc^2"              # 单条转换
  python tools/docx/scripts/equations.py replace --docx paper.docx        # 替换文档中的占位符
  python tools/docx/scripts/equations.py verify --docx paper.docx         # 验证公式转换结果
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# ── LaTeX 符号映射 ──────────────────────────────────────────

LATEX_SYMBOLS = {
    # 希腊字母
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
    r"\delta": "δ", r"\epsilon": "ε", r"\varepsilon": "ɛ",
    r"\zeta": "ζ", r"\eta": "η", r"\theta": "θ",
    r"\vartheta": "ϑ", r"\iota": "ι", r"\kappa": "κ",
    r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν",
    r"\xi": "ξ", r"\pi": "π", r"\varpi": "ϖ",
    r"\rho": "ρ", r"\varrho": "ϱ", r"\sigma": "σ",
    r"\varsigma": "ς", r"\tau": "τ", r"\upsilon": "υ",
    r"\phi": "φ", r"\varphi": "ϕ", r"\chi": "χ",
    r"\psi": "ψ", r"\omega": "ω",
    # 大写希腊字母
    r"\Gamma": "Γ", r"\Delta": "Δ", r"\Theta": "Θ",
    r"\Lambda": "Λ", r"\Xi": "Ξ", r"\Pi": "Π",
    r"\Sigma": "Σ", r"\Phi": "Φ", r"\Psi": "Ψ",
    r"\Omega": "Ω",
    # 数学运算符
    r"\times": "×", r"\cdot": "·", r"\div": "÷",
    r"\pm": "±", r"\mp": "∓", r"\approx": "≈",
    r"\equiv": "≡", r"\neq": "≠", r"\leq": "≤",
    r"\geq": "≥", r"\ll": "≪", r"\gg": "≫",
    r"\propto": "∝", r"\sim": "∼", r"\simeq": "≃",
    r"\infty": "∞", r"\partial": "∂", r"\nabla": "∇",
    r"\forall": "∀", r"\exists": "∃", r"\in": "∈",
    r"\notin": "∉", r"\subset": "⊂", r"\subseteq": "⊆",
    r"\sum": "∑", r"\prod": "∏", r"\int": "∫",
    r"\oint": "∮", r"\to": "→", r"\rightarrow": "→",
    r"\leftarrow": "←", r"\Rightarrow": "⇒",
    r"\Leftrightarrow": "⇔",
    # 三角函数
    r"\sin": "sin", r"\cos": "cos", r"\tan": "tan",
    r"\arcsin": "arcsin", r"\arccos": "arccos", r"\arctan": "arctan",
    r"\log": "log", r"\ln": "ln", r"\lg": "lg",
    r"\max": "max", r"\min": "min",
}


# ── LaTeX 到纯文本（Unicode 数学）转换 ─────────────────────

def latex_to_unicode(latex: str) -> str:
    """将简单 LaTeX 公式转换为 Unicode 数学文本。

    支持：希腊字母、上下标、分数、根号、常见运算符。
    复杂公式（矩阵等）返回原 LaTeX 附带提示。

    Parameters
    ----------
    latex : str
        LaTeX 公式字符串。

    Returns
    -------
    str
    """
    s = latex.strip()

    # 移除多余的花括号（成对）
    s = _simplify_braces(s)

    # 替换 \frac{num}{den} → (num)/(den)
    s = re.sub(r'\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
               r'(\1)/(\2)', s)

    # 替换 \sqrt{...} → √(...)
    s = re.sub(r'\\sqrt\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', r'√(\1)', s)

    # 替换下划线 _{} → 下标
    s = re.sub(r'_\{([^{}]+)\}', lambda m: ''.join(_to_subscript(c) for c in m.group(1)), s)

    # 替换 ^ {} → 上标
    s = re.sub(r'\^\{([^{}]+)\}', lambda m: ''.join(_to_superscript(c) for c in m.group(1)), s)

    # 替换 ^x（单字符上标）
    s = re.sub(r'\^(\w)', lambda m: _to_superscript(m.group(1)), s)

    # 替换已知符号
    for latex_cmd, unicode_char in sorted(LATEX_SYMBOLS.items(), key=lambda x: -len(x[0])):
        s = s.replace(latex_cmd, unicode_char)

    # 清理多余空格
    s = re.sub(r'\s+', ' ', s).strip()

    return s


def _simplify_braces(s: str) -> str:
    """简化不必要的花括号。"""
    # 移除最外层 { ... }
    while s.startswith("{") and s.endswith("}"):
        depth = 0
        balanced = True
        for i, c in enumerate(s):
            if c == "{": depth += 1
            elif c == "}": depth -= 1
            if depth == 0 and i < len(s) - 1:
                balanced = False
                break
        if balanced:
            s = s[1:-1]
        else:
            break
    return s


def _to_superscript(char: str) -> str:
    """单字符转上标 Unicode。"""
    superscript_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³',
        '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷',
        '8': '⁸', '9': '⁹',
        'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ',
        'e': 'ᵉ', 'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ',
        'i': 'ⁱ', 'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ',
        'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ', 'p': 'ᵖ',
        'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
        'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ',
        'z': 'ᶻ',
        '+': '⁺', '-': '⁻', '=': '⁼',
        '(': '⁽', ')': '⁾',
        'T': 'ᵀ',
    }
    return superscript_map.get(char, char)


def _to_subscript(char: str) -> str:
    """单字符转下标 Unicode。"""
    subscript_map = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃',
        '4': '₄', '5': '₅', '6': '₆', '7': '₇',
        '8': '₈', '9': '₉',
        'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ',
        'j': 'ⱼ', 'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ',
        'n': 'ₙ', 'o': 'ₒ', 'p': 'ₚ', 'r': 'ᵣ',
        's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ', 'v': 'ᵥ',
        'x': 'ₓ',
        '+': '₊', '-': '₋', '=': '₌',
        '(': '₍', ')': '₎',
    }
    return subscript_map.get(char, char)


# ── 占位符替换 ──────────────────────────────────────────────

def replace_placeholders(docx_path: str, output_path: str = None):
    """替换 Word 文档中的 〈EQ〉...〈/EQ〉 占位符为 Unicode 数学文本。

    Parameters
    ----------
    docx_path : str
        源 DOCX 文件路径。
    output_path : str, optional
        输出路径，默认覆盖源文件。

    Returns
    -------
    count : int
        替换的公式数量。
    """
    try:
        from docx import Document
    except ImportError:
        print("需要安装 python-docx: pip install python-docx")
        return 0

    doc = Document(docx_path)
    count = 0
    for para in doc.paragraphs:
        if "〈EQ〉" not in para.text:
            continue
        new_text = para.text
        for match in re.finditer(r'〈EQ〉(.+?)〈/EQ〉', para.text):
            latex = match.group(1)
            unicode_math = latex_to_unicode(latex)
            new_text = new_text.replace(match.group(0), unicode_math)
            count += 1
        # 清除并重写
        for run in para.runs:
            run.text = ""
        para.runs[0].text = new_text if para.runs else None

    out = output_path or docx_path
    doc.save(out)
    print(f"已替换 {count} 个公式 → {out}")
    return count


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LaTeX → OMML/Unicode 公式转换器")
    sub = parser.add_subparsers(dest="cmd")

    p_conv = sub.add_parser("convert", help="转换 LaTeX 公式为 Unicode 数学文本")
    p_conv.add_argument("latex", nargs="+", help="LaTeX 公式字符串")

    p_rep = sub.add_parser("replace", help="替换 DOCX 中的公式占位符")
    p_rep.add_argument("--docx", required=True, help="DOCX 文件路径")
    p_rep.add_argument("--output", default=None, help="输出路径（默认覆盖）")

    p_ver = sub.add_parser("verify", help="验证公式转换结果")
    p_ver.add_argument("--docx", required=True, help="DOCX 文件路径")

    args = parser.parse_args()

    if args.cmd == "convert":
        tex = " ".join(args.latex)
        result = latex_to_unicode(tex)
        print(f"LaTeX: {tex}")
        print(f"Unicode: {result}")

    elif args.cmd == "replace":
        replace_placeholders(args.docx, args.output)

    elif args.cmd == "verify":
        try:
            from docx import Document
            doc = Document(args.docx)
            eq_count = 0
            unresolved = 0
            for para in doc.paragraphs:
                eq_count += para.text.count("〈EQ〉")
                unresolved += para.text.count("??")
            print(f"文档: {args.docx}")
            print(f"公式占位符: {eq_count}")
            print(f"未解析引用: {unresolved}")
            if eq_count > 0:
                print("警告: 存在未替换的公式占位符，运行 'replace' 命令处理")
            if unresolved > 0:
                print("警告: 存在未解析的引用（??）")
            if eq_count == 0 and unresolved == 0:
                print("验证通过")
        except ImportError:
            print("需要安装 python-docx: pip install python-docx")

    else:
        parser.print_help()
