#!/usr/bin/env python3
"""
Word 论文格式化 — paper_format.py
====================================
使用 python-docx 生成符合竞赛格式的 Word 论文。
支持：页边距设置、标题/正文格式、三线表、OMML 公式插入。

用法：
  python tools/docx/scripts/paper_format.py validate --docx 完整论文.docx
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from docx import Document
    from docx.shared import Pt, Cm, Inches, RGBColor, Emu
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn, nsdecls
    from docx.oxml import parse_xml
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


# ── 竞赛配置 ────────────────────────────────────────────────

CONTEST_PROFILES = {
    "cumcm": {
        "page_size": "A4",
        "margin_top_cm": 2.54,
        "margin_bottom_cm": 2.54,
        "margin_left_cm": 3.18,
        "margin_right_cm": 3.18,
        "body_font_name": "宋体",
        "body_font_size_pt": 12,
        "heading1_font_name": "黑体",
        "heading1_font_size_pt": 14,
        "line_spacing": 1.25,
    },
}


# ── 文档创建与设置 ──────────────────────────────────────────

def new_document() -> "Document":
    """创建新的 Word 文档。"""
    if not HAS_DOCX:
        raise ImportError("需要安装 python-docx: pip install python-docx")
    return Document()


def setup_page(doc: "Document", contest: str = "cumcm"):
    """设置页边距和页面大小。"""
    profile = CONTEST_PROFILES.get(contest, CONTEST_PROFILES["cumcm"])
    for section in doc.sections:
        section.top_margin = Cm(profile["margin_top_cm"])
        section.bottom_margin = Cm(profile["margin_bottom_cm"])
        section.left_margin = Cm(profile["margin_left_cm"])
        section.right_margin = Cm(profile["margin_right_cm"])


# ── 段落与文字 ──────────────────────────────────────────────

def _set_run_font(run, name: str = "宋体", size_pt: float = 12,
                  bold: bool = False, color=None):
    """设置 run 的字体属性。"""
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def _add_paragraph(doc, text: str, font_name: str, size_pt: float,
                   bold: bool = False, alignment=None, space_after_pt: float = 6):
    """添加一个格式化段落。"""
    p = doc.add_paragraph()
    if alignment is not None:
        p.alignment = alignment
    pf = p.paragraph_format
    pf.space_after = Pt(space_after_pt)
    pf.line_spacing = 1.25
    run = p.add_run(text)
    _set_run_font(run, font_name, size_pt, bold)
    return p


def title(doc, text: str):
    """论文标题（黑体 16pt 居中）。"""
    return _add_paragraph(doc, text, "黑体", 16, bold=True,
                          alignment=WD_ALIGN_PARAGRAPH.CENTER)

def heading1(doc, text: str):
    """一级标题（黑体 14pt）。"""
    return _add_paragraph(doc, text, "黑体", 14, bold=True, space_after_pt=12)

def heading2(doc, text: str):
    """二级标题（黑体 12pt）。"""
    return _add_paragraph(doc, text, "黑体", 12, bold=True, space_after_pt=8)

def body(doc, text: str):
    """正文段落（宋体 12pt，首行缩进 2 字符）。"""
    p = _add_paragraph(doc, text, "宋体", 12)
    p.paragraph_format.first_line_indent = Pt(24)  # ~2 字符
    return p


# ── 三线表 ─────────────────────────────────────────────────

def three_line_table(doc, headers: List[str], rows: List[List[str]],
                     col_widths: Optional[List[float]] = None,
                     caption: str = "") -> "Table":
    """创建学术三线表（顶线、栏目线、底线）。

    Parameters
    ----------
    doc : Document
    headers : list of str
        表头列名。
    rows : list of list of str
        数据行。
    col_widths : list of float, optional
        列宽（厘米）。
    caption : str
        表题（显示在表上方）。

    Returns
    -------
    table : docx.table.Table
    """
    n_rows = len(rows) + 1  # +1 for header
    n_cols = len(headers)
    table = doc.add_table(rows=n_rows, cols=n_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # 设置列宽
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)

    # 填充表头
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        _set_run_font(run, "黑体", 10, bold=True)

    # 填充数据
    for i, row_data in enumerate(rows):
        for j, val in enumerate(row_data):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(val))
            _set_run_font(run, "宋体", 10)

    # 应用三线表边框
    _apply_three_line_borders(table)

    # 表题
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(6)
        cp.paragraph_format.space_after = Pt(3)
        run = cp.add_run(caption)
        _set_run_font(run, "黑体", 10)

    return table


def _apply_three_line_borders(table):
    """为表格应用三线表边框（顶线、栏目线、底线加粗，其余无边框）。"""
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else parse_xml(f'<w:tblPr {nsdecls("w")}></w:tblPr>')

    # 设置表格边框为无
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '  <w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
        '  <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '  <w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
        '  <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '  <w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '  <w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '</w:tblBorders>'
    )
    tblPr.append(borders)

    # 栏目线（表头行底部加粗）
    if len(table.rows) > 0:
        for cell in table.rows[0].cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                '  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
                '</w:tcBorders>'
            )
            tcPr.append(tcBorders)


# ── 公式插入（OMML 占位） ───────────────────────────────────

def equation(doc, latex: str) -> "Paragraph":
    """插入 LaTeX 公式（使用 OMML 占位符，待 equations.py 转换）。

    如果运行环境中没有 OMML 转换功能，则插入 LaTeX 源码作为占位符，
    后续可用 tools/docx/scripts/equations.py 进行批量转换。

    Parameters
    ----------
    doc : Document
    latex : str
        LaTeX 公式源码（如 "E = mc^2"）。

    Returns
    -------
    paragraph
    """
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # 使用特殊标记以便后续替换
    run = p.add_run(f"〈EQ〉{latex}〈/EQ〉")
    _set_run_font(run, "Cambria Math", 11)
    return p


# ── 文档校验 ────────────────────────────────────────────────

def count_chinese_chars(text: str) -> int:
    """统计中文字符数。"""
    return len(re.findall(r'[一-鿿]', text))


def validate_paper_structure(doc: "Document", contest: str = "cumcm",
                             rendered_pages: int = None) -> dict:
    """校验论文结构。

    Parameters
    ----------
    doc : Document
    contest : str
    rendered_pages : int, optional
        编译后的实际页数。

    Returns
    -------
    dict with keys: ok, issues, warnings, stats
    """
    issues = []
    warnings = []

    # 统计
    total_chars = 0
    eq_count = 0
    fig_count = 0
    tab_count = 0
    for para in doc.paragraphs:
        total_chars += count_chinese_chars(para.text)
        if "〈EQ〉" in para.text:
            eq_count += 1
        if "图" in para.text and ("图1" <= para.text[:5] <= "图9" or "fig" in para.text.lower()):
            fig_count += 1
    tab_count = len(doc.tables)

    estimated_pages = max(1, total_chars // 800)  # 800中文字 ≈ 1页

    stats = {
        "chinese_chars": total_chars,
        "equations": eq_count,
        "figures": fig_count,
        "tables": tab_count,
        "estimated_pages": estimated_pages,
    }

    # 校验
    if contest == "cumcm":
        if rendered_pages and rendered_pages > 30:
            issues.append(f"正文 {rendered_pages} 页 > 30 页上限")
        if eq_count < 5:
            warnings.append(f"公式 {eq_count} 个（建议≥5）")
        if tab_count < 3:
            warnings.append(f"表格 {tab_count} 个（建议≥3）")
        if total_chars < 8000:
            warnings.append(f"中文字数 {total_chars}（偏少，建议≥10000）")

    ok = len(issues) == 0
    return {"ok": ok, "issues": issues, "warnings": warnings, "stats": stats}


def save_document(doc: "Document", path: str):
    """安全保存文档（原子写入）。"""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    doc.save(str(tmp))
    tmp.replace(out)
    print(f"论文已保存: {out}")


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Word 论文格式化工具")
    sub = parser.add_subparsers(dest="cmd")

    p_val = sub.add_parser("validate", help="校验 Word 论文")
    p_val.add_argument("--docx", required=True, help="论文 DOCX 文件路径")
    p_val.add_argument("--contest", default="cumcm")
    p_val.add_argument("--pages", type=int, default=None,
                       help="编译后实际页数")

    args = parser.parse_args()

    if args.cmd == "validate":
        doc = Document(args.docx)
        result = validate_paper_structure(doc, args.contest, args.pages)
        print("=" * 45)
        print("Word 论文校验报告")
        print("=" * 45)
        s = result["stats"]
        print(f"中文字数: {s['chinese_chars']}")
        print(f"公式: {s['equations']}（建议≥5）")
        print(f"表格: {s['tables']}（建议≥3）")
        print(f"估计页数: {s['estimated_pages']}（上限30）")
        if result["issues"]:
            print(f"\n问题 ({len(result['issues'])}):")
            for i, iss in enumerate(result["issues"], 1):
                print(f"  {i}. {iss}")
        if result["warnings"]:
            print(f"\n警告 ({len(result['warnings'])}):")
            for i, w in enumerate(result["warnings"], 1):
                print(f"  {i}. {w}")
        verdict = "PASS" if result["ok"] else "FAIL"
        print(f"\n{'─' * 45}\n结果: {verdict}\n{'─' * 45}")
        import sys
        sys.exit(0 if result["ok"] else 1)
    else:
        parser.print_help()
