#!/usr/bin/env python3
"""
论文自动审计脚本 — paper_audit.py
===================================
在 W2 质量门 Subagent 之前运行，秒级拦截硬错误：
  1. 图表引用完整性 — figures/ 中的图是否在论文中被引用
  2. 章节结构检查 — 标题层级是否匹配模板要求
  3. 数值交叉校验 — 论文中关键数值 vs results/ 中的 CSV
  4. 编译检查 — LaTeX 能否成功编译
  5. 提交清单生成 — 所有提交材料是否就绪

无外部依赖（仅标准库 + 可选 LaTeX），可在任何 Python 3.8+ 环境运行。

用法：
  python paper_audit.py <paper.tex> --figures-dir figures/ --results-dir results/
  python paper_audit.py <paper.docx> --figures-dir figures/
  python paper_audit.py <paper.tex> --compile          # 同时检查 LaTeX 编译
  python paper_audit.py <paper.tex> --strict            # 不通过则 exit 1
"""

import csv
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


# ══════════════════════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════════════════════

def _find_files(directory: str, patterns: list) -> list:
    """在目录中查找匹配扩展名的文件。"""
    files = []
    p = Path(directory)
    if not p.is_dir():
        return files
    for pat in patterns:
        files.extend(sorted(p.glob(pat)))
    return files


def _read_file_text(filepath: str) -> str:
    """读取文本文件，自动处理编码。"""
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 最后尝试忽略错误
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _extract_numbers_from_text(text: str) -> dict:
    """从文本中提取所有数值及其上下文（用于交叉校验）。

    返回 {数值: [上下文片段列表]} 的字典。
    数值匹配：带或不带单位的浮点数、百分数、科学计数法。
    """
    patterns = [
        # 百分数
        (r'(\d+\.?\d*)\s*%', lambda m: f"{float(m.group(1)):.2f}%"),
        # 科学计数法
        (r'(\d+\.?\d*[eE][+-]?\d+)', lambda m: f"{float(m.group(1)):.4e}"),
        # 普通小数（≥4 位有效数字才收录，避免匹配章节号等）
        (r'(?<![\.\d])(\d{1,3}(?:,\d{3})*(?:\.\d{3,}))(?![\.\d])', lambda m: m.group(1)),
        (r'(?<![\.\d])(\d+\.\d{3,})(?![\.\d])', lambda m: m.group(1)),
    ]
    found = {}
    for pat, normalizer in patterns:
        for m in re.finditer(pat, text):
            val = normalizer(m)
            if val not in found:
                found[val] = []
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            ctx = text[start:end].replace('\n', ' ').strip()
            found[val].append(ctx)
    return found


def _extract_numbers_from_csv(filepath: str) -> dict:
    """从 CSV 中提取关键数值（跳过表头和文本列）。"""
    nums = {}
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            for row in reader:
                for col_idx, cell in enumerate(row):
                    cell = cell.strip()
                    try:
                        v = float(cell.replace(",", "").replace(" ", ""))
                        key = f"{abs(v):.4f}"
                        if key not in nums:
                            nums[key] = []
                        col_name = header[col_idx] if col_idx < len(header) else f"col{col_idx}"
                        nums[key].append({"file": filepath, "column": col_name, "value": v, "raw": cell})
                    except (ValueError, AttributeError):
                        continue
    except Exception:
        pass
    return nums


# ══════════════════════════════════════════════════════════════
#  检查 1：图表引用完整性
# ══════════════════════════════════════════════════════════════

def _check_figure_references(paper_text: str, figures_dir: str) -> dict:
    """检查 figures/ 中的图片是否都在论文中被引用。"""
    issues = []
    warnings = []

    png_files = _find_files(figures_dir, ["*.png"])
    svg_files = _find_files(figures_dir, ["*.svg"])
    figure_stems = set()
    for f in png_files + svg_files:
        figure_stems.add(Path(f).stem)

    # LaTeX 引用模式
    latex_refs = set()
    for m in re.finditer(r'\\includegraphics\{.*?([^/]+)\}', paper_text):
        stem = Path(m.group(1)).stem
        latex_refs.add(stem)
    # \label{fig:xxx} 引用
    for m in re.finditer(r'\\label\{fig:([^}]+)\}', paper_text):
        latex_refs.add(m.group(1))
    # Word 图片引用（占位符模式）
    word_refs = set()
    for m in re.finditer(r'!\[([^\]]*)\]\(figures/([^)]+)\)', paper_text):
        word_refs.add(Path(m.group(2)).stem)

    all_refs = latex_refs | word_refs

    # 未被引用的图片
    unreferenced = figure_stems - all_refs
    # 被引用但不存在的图片
    missing = all_refs - figure_stems

    if unreferenced:
        warnings.append(f"图片未被引用: {sorted(unreferenced)}")
    if missing:
        issues.append(f"论文引用了不存在的图片: {sorted(missing)}")

    return {
        "ok": len(issues) == 0,
        "figure_count": len(figure_stems),
        "ref_count": len(all_refs),
        "unreferenced": sorted(unreferenced),
        "missing": sorted(missing),
        "issues": issues,
        "warnings": warnings,
    }


def _check_table_references(paper_text: str) -> dict:
    """检查表格引用——所有 \\label{tab:xxx} 是否被 \\ref{tab:xxx} 引用。"""
    issues = []
    warnings = []

    # 查找所有表格标签
    table_labels = set(re.findall(r'\\label\{tab:([^}]+)\}', paper_text))
    # 查找所有表格引用
    table_refs = set()
    for m in re.finditer(r'\\ref\{tab:([^}]+)\}', paper_text):
        table_refs.add(m.group(1))
    # \autoref 模式
    for m in re.finditer(r'\\autoref\{tab:([^}]+)\}', paper_text):
        table_refs.add(m.group(1))

    unreferenced = table_labels - table_refs
    missing = table_refs - table_labels

    if unreferenced:
        warnings.append(f"表格标签未被引用: {sorted(unreferenced)}")
    if missing:
        issues.append(f"引用了不存在的表格标签: {sorted(missing)}")

    return {
        "ok": len(issues) == 0,
        "table_label_count": len(table_labels),
        "table_ref_count": len(table_refs),
        "unreferenced": sorted(unreferenced),
        "missing": sorted(missing),
        "issues": issues,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════
#  检查 2：章节结构检查
# ══════════════════════════════════════════════════════════════

# 竞赛论文标准结构
STANDARD_SECTIONS = [
    "问题重述",
    "模型假设",
    "符号说明",
    "模型建立与求解",
    "模型评价与推广",
    "参考文献",
    "附录",
]

# 可接受的别名映射
SECTION_ALIASES = {
    "模型建立及求解": "模型建立与求解",
    "模型的建立与求解": "模型建立与求解",
    "模型的建立及求解": "模型建立与求解",
    "问题分析": "符号说明",  # 部分论文合并
    "模型假设与符号说明": "模型假设",
    "结果分析": "模型建立与求解",
    "模型的评价与推广": "模型评价与推广",
    "模型优缺点": "模型评价与推广",
    "模型评价": "模型评价与推广",
    "问题重述与分析": "问题重述",
    "问题背景": "问题重述",
    "reference": "参考文献",
    "references": "参考文献",
}


def _check_section_structure(paper_text: str) -> dict:
    """检查论文章节结构是否符合竞赛规范。"""
    issues = []
    warnings = []

    # 提取 LaTeX section 标题
    section_pattern = r'\\(?:section|subsection|subsubsection)\*?\s*\{([^}]+)\}'
    sections = re.findall(section_pattern, paper_text)

    # 映射为标准名称
    mapped = []
    for s in sections:
        s_clean = s.strip()
        mapped.append(SECTION_ALIASES.get(s_clean, s_clean))

    found_set = set(mapped)

    # 检查必需章节
    required = ["问题重述", "模型建立与求解", "模型评价与推广", "参考文献"]
    for req in required:
        if req not in found_set:
            issues.append(f"缺少必要章节: {req}")

    # 检查页数（粗略估算：每 3000 字符 ≈ 1 页）
    char_count = len(paper_text)
    estimated_pages = char_count / 3000
    if estimated_pages > 30:
        warnings.append(f"正文偏长（估计 {estimated_pages:.0f} 页，上限 30 页）")
    if estimated_pages < 5:
        warnings.append(f"正文偏短（估计 {estimated_pages:.0f} 页）")

    # 摘要检查
    has_abstract = bool(re.search(
        r'\\begin\{abstract\}|\\section\*\{摘\s*要\}|摘\s*要',
        paper_text
    ))
    if not has_abstract:
        issues.append("未找到摘要")

    # 关键词检查
    has_keywords = bool(re.search(r'关键[词字]', paper_text))
    if not has_keywords:
        warnings.append("未找到关键词")

    return {
        "ok": len(issues) == 0,
        "sections_found": [s.strip() for s in sections],
        "mapped_sections": mapped,
        "missing_required": [r for r in required if r not in found_set],
        "estimated_pages": round(estimated_pages, 1),
        "char_count": char_count,
        "has_abstract": has_abstract,
        "has_keywords": has_keywords,
        "issues": issues,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════
#  检查 3：数值交叉校验
# ══════════════════════════════════════════════════════════════

def _check_numerical_consistency(paper_text: str, results_dir: str) -> dict:
    """交叉校验论文中引用的数值与 results/ 中的计算结果。"""
    issues = []
    warnings = []

    paper_nums = _extract_numbers_from_text(paper_text)
    if not paper_nums:
        return {
            "ok": True, "paper_number_count": 0, "csv_number_count": 0,
            "matched": [], "unmatched_paper": [], "issues": [], "warnings":
            ["论文中未提取到可交叉校验的数值"]
        }

    csv_dir = Path(results_dir)
    if not csv_dir.is_dir():
        return {
            "ok": True, "paper_number_count": len(paper_nums),
            "csv_number_count": 0, "matched": [], "unmatched_paper": [],
            "issues": [], "warnings": [f"results 目录不存在: {results_dir}"]
        }

    # 汇总所有 CSV 中的数值
    all_csv_nums = {}
    for csv_file in sorted(csv_dir.glob("*.csv")):
        csv_nums = _extract_numbers_from_csv(str(csv_file))
        for k, v in csv_nums.items():
            if k not in all_csv_nums:
                all_csv_nums[k] = []
            all_csv_nums[k].extend(v)

    # 在论文数值和 CSV 数值之间寻找可能匹配
    # 使用近似匹配（相对误差 < 1%）
    matched = []
    unmatched_paper = []

    paper_vals = {}
    for val_str in paper_nums:
        try:
            val_str_clean = val_str.replace("%", "").replace(",", "")
            paper_vals[val_str] = float(val_str_clean)
        except ValueError:
            continue

    csv_vals = {}
    for val_str in all_csv_nums:
        try:
            csv_vals[val_str] = float(val_str.replace(",", ""))
        except ValueError:
            continue

    for p_str, p_val in paper_vals.items():
        found = False
        for c_str, c_val in csv_vals.items():
            if c_val == 0 and p_val == 0:
                found = True
                matched.append({"paper_value": p_str, "csv_value": c_str, "source": all_csv_nums[c_str]})
                break
            elif c_val != 0:
                rel_err = abs(p_val - c_val) / abs(c_val)
                if rel_err < 0.01:
                    found = True
                    matched.append({"paper_value": p_str, "csv_value": c_str, "source": all_csv_nums[c_str]})
                    break
        if not found:
            unmatched_paper.append(p_str)

    if not matched:
        warnings.append("未找到论文与结果文件的数值匹配（可能是格式差异或数值已四舍五入）")
    if unmatched_paper and len(unmatched_paper) > len(paper_vals) * 0.5:
        warnings.append(f"论文中 {len(unmatched_paper)}/{len(paper_vals)} 个数值在结果文件中无匹配")

    return {
        "ok": len(issues) == 0,
        "paper_number_count": len(paper_vals),
        "csv_number_count": len(csv_vals),
        "matched_count": len(matched),
        "unmatched_count": len(unmatched_paper),
        "matched": matched[:10],  # 最多展示 10 组匹配
        "unmatched_paper": unmatched_paper[:10],
        "issues": issues,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════
#  检查 4：LaTeX 编译检查
# ══════════════════════════════════════════════════════════════

def _check_latex_compilation(tex_path: str) -> dict:
    """尝试编译 LaTeX 文件，检查是否有编译错误。"""
    tex_path = Path(tex_path).resolve()
    if not tex_path.exists():
        return {"ok": False, "issues": [f"LaTeX 文件不存在: {tex_path}"], "warnings": []}

    # 检测可用的 LaTeX 引擎
    engines = []
    for eng in ["xelatex", "pdflatex", "lualatex"]:
        try:
            result = subprocess.run(
                [eng, "--version"],
                capture_output=True, text=True, timeout=5,
                **({"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {})
            )
            if result.returncode == 0:
                engines.append(eng)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    if not engines:
        return {
            "ok": True,
            "engines_available": [],
            "issues": [],
            "warnings": ["未检测到可用的 LaTeX 引擎（跳过编译检查）"],
        }

    # 使用第一个可用引擎尝试编译
    engine = engines[0]
    work_dir = tex_path.parent
    tex_name = tex_path.name

    try:
        result = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", tex_name],
            capture_output=True, text=True, timeout=60,
            cwd=str(work_dir),
            **({"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {})
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "engines_available": engines,
            "engine_used": engine,
            "issues": ["LaTeX 编译超时（>60s）"],
            "warnings": [],
        }

    stdout = result.stdout + result.stderr

    # 解析编译输出
    errors = []
    warnings = []
    for line in stdout.splitlines():
        if line.startswith("!"):
            errors.append(line.strip())
        elif "Warning" in line and ("undefined" in line.lower() or "overfull" in line.lower() or "underfull" in line.lower()):
            warnings.append(line.strip())

    # 严重错误（阻止生成 PDF）
    fatal_errors = [e for e in errors if "Emergency stop" in e or "Fatal error" in e]

    issues = []
    if fatal_errors:
        issues.append(f"LaTeX 编译失败（{engine}）: {len(fatal_errors)} 个致命错误")
        issues.extend(fatal_errors[:5])
    elif errors:
        issues.append(f"LaTeX 编译有 {len(errors)} 个错误（{engine}）")
        issues.extend(errors[:5])

    # 检查是否生成了 PDF
    pdf_path = tex_path.with_suffix(".pdf")
    pdf_generated = pdf_path.exists()

    return {
        "ok": len(fatal_errors) == 0,
        "engines_available": engines,
        "engine_used": engine,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "fatal_count": len(fatal_errors),
        "pdf_generated": pdf_generated,
        "errors": errors[:10],
        "warnings_list": warnings[:20],
        "issues": issues,
        "warnings": [],
    }


# ══════════════════════════════════════════════════════════════
#  检查 5：提交清单
# ══════════════════════════════════════════════════════════════

SUBMISSION_ITEMS = [
    ("论文 PDF", ["paper.pdf", "*.pdf"]),
    ("可运行代码", ["code/main.py"]),
    ("结果文件", ["results/"]),
    ("图表文件", ["figures/"]),
    ("复现清单", ["results/复现清单.json"]),
    ("AI 使用台账", ["references/AI使用台账模板.md"]),
]


def _check_submission_readiness(project_root: str) -> dict:
    """检查提交材料是否齐全。"""
    root = Path(project_root)
    ready = []
    missing = []
    warnings = []

    for item_name, paths in SUBMISSION_ITEMS:
        found = False
        for p in paths:
            full = root / p
            if "*" in p:
                matches = list(root.glob(p))
                if matches:
                    found = True
                    break
            elif full.exists():
                found = True
                break
        if found:
            ready.append(item_name)
        else:
            missing.append(item_name)

    if missing:
        warnings.append(f"缺失提交材料: {missing}")

    # 检查 figure 双格式
    figures_dir = root / "figures"
    if figures_dir.is_dir():
        png_count = len(list(figures_dir.glob("*.png")))
        svg_count = len(list(figures_dir.glob("*.svg")))
        if png_count < 9:
            warnings.append(f"PNG 图仅 {png_count} 张（建议 ≥9）")
        if svg_count < png_count:
            warnings.append(f"SVG 图 ({svg_count}) 少于 PNG ({png_count})，存在未配对的 PNG")

    return {
        "ok": len(missing) == 0,
        "ready_items": ready,
        "missing_items": missing,
        "issues": [],
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════
#  DOCX 支持（基础结构检查）
# ══════════════════════════════════════════════════════════════

def _check_docx_structure(docx_path: str) -> dict:
    """对 DOCX 文件做基本结构检查（解析 XML）。"""
    import zipfile
    issues = []
    warnings = []

    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            if "word/document.xml" not in z.namelist():
                return {"ok": False, "issues": ["无效的 DOCX 文件：缺少 word/document.xml"], "warnings": []}
            doc_xml = z.read("word/document.xml").decode("utf-8")
    except Exception as e:
        return {"ok": False, "issues": [f"无法读取 DOCX: {e}"], "warnings": []}

    # 检查段落/标题
    body_match = re.search(r'<w:body>(.*?)</w:body>', doc_xml, re.DOTALL)
    if not body_match:
        return {"ok": False, "issues": ["DOCX 缺少 body 元素"], "warnings": []}

    body = body_match.group(1)

    # 统计段落数
    para_count = len(re.findall(r'<w:p[ >]', body))
    if para_count < 20:
        warnings.append(f"DOCX 段落数偏少 ({para_count})")
    if para_count > 500:
        warnings.append(f"DOCX 段落数偏多 ({para_count})，检查是否超出 30 页上限")

    # 检查图片引用（DOCX 内嵌图片）
    image_count = len(re.findall(r'<wp:inline', body)) + len(re.findall(r'<wp:anchor', body))
    if image_count < 3:
        warnings.append(f"DOCX 中图片仅 {image_count} 张（建议 ≥5）")

    # 检查表格
    table_count = len(re.findall(r'<w:tbl>', body))
    if table_count == 0:
        warnings.append("DOCX 中未检测到表格")

    # 字符数估计
    char_count = len(re.findall(r'<w:t[ >][^<]*</w:t>', body))
    estimated_pages = char_count / 2000
    if estimated_pages > 30:
        warnings.append(f"DOCX 正文偏长（估计 {estimated_pages:.0f} 页，上限 30 页）")

    return {
        "ok": len(issues) == 0,
        "paragraph_count": para_count,
        "image_count": image_count,
        "table_count": table_count,
        "estimated_pages": round(estimated_pages, 1),
        "issues": issues,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════
#  主审计函数
# ══════════════════════════════════════════════════════════════

def audit_paper(
    paper_path: str,
    figures_dir: str = "figures",
    results_dir: str = "results",
    compile_check: bool = False,
    project_root: str = None,
    strict: bool = False,
) -> dict:
    """
    对论文执行全面自动审计。

    Parameters
    ----------
    paper_path : str
        论文文件路径 (.tex 或 .docx)
    figures_dir : str
        图片目录路径
    results_dir : str
        结果文件目录路径
    compile_check : bool
        是否检查 LaTeX 编译
    project_root : str
        项目根目录（用于提交清单检查）
    strict : bool
        严格模式：有问题则判定 FAIL

    Returns
    -------
    dict with keys: ok, checks, issues, warnings
    """
    paper_path = Path(paper_path)
    if not paper_path.exists():
        return {"ok": False, "issues": [f"论文文件不存在: {paper_path}"], "warnings": [], "checks": {}}

    ext = paper_path.suffix.lower()
    is_tex = ext == ".tex"
    is_docx = ext == ".docx"

    if not is_tex and not is_docx:
        return {
            "ok": False,
            "issues": [f"不支持的论文格式: {ext}（仅支持 .tex / .docx）"],
            "warnings": [],
            "checks": {},
        }

    issues = []
    warnings = []
    checks = {}

    # ── 文本读取 ──
    if is_tex:
        paper_text = _read_file_text(str(paper_path))
    else:
        paper_text = ""  # DOCX 不直接读文本

    # ── 检查 1：图表引用 ──
    if is_tex and figures_dir:
        fr = _check_figure_references(paper_text, figures_dir)
        checks["figure_references"] = fr
        issues.extend(fr.get("issues", []))
        warnings.extend(fr.get("warnings", []))
    else:
        checks["figure_references"] = {"ok": True, "note": "跳过（DOCX 图表检查见下方 docx_structure）"}

    # ── 检查 2：表格引用 ──
    if is_tex:
        tr = _check_table_references(paper_text)
        checks["table_references"] = tr
        issues.extend(tr.get("issues", []))
        warnings.extend(tr.get("warnings", []))
    else:
        checks["table_references"] = {"ok": True, "note": "跳过（仅支持 LaTeX）"}

    # ── 检查 3：章节结构 ──
    if is_tex:
        ss = _check_section_structure(paper_text)
        checks["section_structure"] = ss
        issues.extend(ss.get("issues", []))
        warnings.extend(ss.get("warnings", []))
    elif is_docx:
        ds = _check_docx_structure(str(paper_path))
        checks["docx_structure"] = ds
        issues.extend(ds.get("issues", []))
        warnings.extend(ds.get("warnings", []))

    # ── 检查 4：数值交叉校验 ──
    if is_tex and results_dir:
        nc = _check_numerical_consistency(paper_text, results_dir)
        checks["numerical_consistency"] = nc
        issues.extend(nc.get("issues", []))
        warnings.extend(nc.get("warnings", []))
    else:
        checks["numerical_consistency"] = {"ok": True, "note": "跳过（仅 LaTeX + results 目录可用时执行）"}

    # ── 检查 5：LaTeX 编译 ──
    if is_tex and compile_check:
        lc = _check_latex_compilation(str(paper_path))
        checks["latex_compilation"] = lc
        issues.extend(lc.get("issues", []))
        warnings.extend(lc.get("warnings", []))
    elif is_tex and not compile_check:
        checks["latex_compilation"] = {"ok": True, "note": "跳过（使用 --compile 启用）"}

    # ── 检查 6：提交清单 ──
    if project_root:
        sr = _check_submission_readiness(project_root)
        checks["submission_readiness"] = sr
        issues.extend(sr.get("issues", []))
        warnings.extend(sr.get("warnings", []))
    else:
        checks["submission_readiness"] = {"ok": True, "note": "跳过（未指定 project_root）"}

    ok = len(issues) == 0

    return {
        "ok": ok,
        "paper": str(paper_path.resolve()),
        "format": ext,
        "checks": checks,
        "issues": issues,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════
#  输出
# ══════════════════════════════════════════════════════════════

def print_report(report: dict):
    """美观打印审计报告。"""
    print("=" * 60)
    print("论文自动审计报告")
    print("=" * 60)
    print(f"文件  : {report.get('paper', 'N/A')}")
    print(f"格式  : {report.get('format', 'N/A')}")
    print()

    checks = report.get("checks", {})

    # ── 图表引用 ──
    fr = checks.get("figure_references", {})
    if fr and "note" not in fr:
        print("─ 图表引用 ─")
        print(f"  figures/ 图片: {fr.get('figure_count', 0)} 张")
        print(f"  论文引用: {fr.get('ref_count', 0)} 处")
        if fr.get("unreferenced"):
            print(f"  ⚠ 未被引用的图片: {fr['unreferenced']}")
        if fr.get("missing"):
            print(f"  ❌ 引用不存在的图片: {fr['missing']}")
        if fr.get("ok"):
            print(f"  状态: PASS")
        else:
            print(f"  状态: FAIL")
        print()

    tr = checks.get("table_references", {})
    if tr and "note" not in tr:
        print("─ 表格引用 ─")
        print(f"  表格标签: {tr.get('table_label_count', 0)} 个")
        print(f"  表格引用: {tr.get('table_ref_count', 0)} 处")
        if tr.get("unreferenced"):
            print(f"  ⚠ 未被引用的表格: {tr['unreferenced']}")
        if tr.get("missing"):
            print(f"  ❌ 引用不存在的表格: {tr['missing']}")
        if tr.get("ok"):
            print(f"  状态: PASS")
        else:
            print(f"  状态: FAIL")
        print()

    # ── 章节结构 ──
    ss = checks.get("section_structure", {})
    if ss and "note" not in ss:
        print("─ 章节结构 ─")
        print(f"  检测到的章节: {ss.get('sections_found', [])}")
        if ss.get("missing_required"):
            print(f"  ❌ 缺少必要章节: {ss['missing_required']}")
        print(f"  估计页数: {ss.get('estimated_pages', 'N/A')} 页")
        print(f"  摘要: {'有' if ss.get('has_abstract') else '❌ 缺失'}")
        print(f"  关键词: {'有' if ss.get('has_keywords') else '⚠ 未检测到'}")
        if ss.get("ok"):
            print(f"  状态: PASS")
        else:
            print(f"  状态: FAIL")
        print()

    # ── DOCX 结构 ──
    ds = checks.get("docx_structure", {})
    if ds and "note" not in ds:
        print("─ DOCX 结构 ─")
        print(f"  段落数: {ds.get('paragraph_count', 'N/A')}")
        print(f"  图片数: {ds.get('image_count', 'N/A')}")
        print(f"  表格数: {ds.get('table_count', 'N/A')}")
        print(f"  估计页数: {ds.get('estimated_pages', 'N/A')} 页")
        if ds.get("ok"):
            print(f"  状态: PASS")
        else:
            print(f"  状态: FAIL")
        print()

    # ── 数值交叉校验 ──
    nc = checks.get("numerical_consistency", {})
    if nc and "note" not in nc:
        print("─ 数值交叉校验 ─")
        print(f"  论文数值: {nc.get('paper_number_count', 0)} 个")
        print(f"  CSV 数值: {nc.get('csv_number_count', 0)} 个")
        print(f"  匹配数: {nc.get('matched_count', 0)}")
        print(f"  未匹配: {nc.get('unmatched_count', 0)}")
        matched = nc.get("matched", [])
        if matched:
            print(f"  匹配示例:")
            for m in matched[:5]:
                print(f"    论文 {m['paper_value']} ≈ CSV {m['csv_value']}")
        if nc.get("ok"):
            print(f"  状态: PASS")
        else:
            print(f"  状态: FAIL")
        print()

    # ── LaTeX 编译 ──
    lc = checks.get("latex_compilation", {})
    if lc and "note" not in lc:
        print("─ LaTeX 编译 ─")
        if not lc.get("engines_available"):
            print(f"  ⚠ {lc.get('warnings', ['无可用引擎'])[0]}")
        else:
            print(f"  引擎: {lc.get('engine_used')}")
            print(f"  错误: {lc.get('error_count', 0)}")
            print(f"  警告: {lc.get('warning_count', 0)}")
            print(f"  PDF 生成: {'是' if lc.get('pdf_generated') else '否'}")
        if lc.get("ok"):
            print(f"  状态: PASS")
        else:
            print(f"  状态: FAIL")
        print()

    # ── 提交清单 ──
    sr = checks.get("submission_readiness", {})
    if sr and "note" not in sr:
        print("─ 提交清单 ─")
        print(f"  就绪: {sr.get('ready_items', [])}")
        if sr.get("missing_items"):
            print(f"  ❌ 缺失: {sr['missing_items']}")
        if sr.get("ok"):
            print(f"  状态: PASS")
        else:
            print(f"  状态: FAIL")
        print()

    # ── 总览 ──
    all_issues = report.get("issues", [])
    all_warnings = report.get("warnings", [])

    if all_issues:
        print(f"问题 ({len(all_issues)}):")
        for i, iss in enumerate(all_issues, 1):
            print(f"  {i}. {iss}")

    if all_warnings:
        print(f"\n提醒 ({len(all_warnings)}):")
        for i, w in enumerate(all_warnings, 1):
            print(f"  {i}. {w}")

    verdict = "PASS" if report["ok"] else "FAIL"
    print(f"\n{'─' * 60}")
    print(f"结果: {verdict}")
    print(f"{'─' * 60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="论文自动审计脚本")
    parser.add_argument("paper", help="论文文件路径 (.tex 或 .docx)")
    parser.add_argument("--figures-dir", default="figures", help="图片目录（默认: figures）")
    parser.add_argument("--results-dir", default="results", help="结果目录（默认: results）")
    parser.add_argument("--compile", action="store_true", help="同时检查 LaTeX 编译")
    parser.add_argument("--project-root", default=None, help="项目根目录（用于提交清单）")
    parser.add_argument("--strict", action="store_true", help="不通过则 exit 1")
    args = parser.parse_args()

    report = audit_paper(
        paper_path=args.paper,
        figures_dir=args.figures_dir,
        results_dir=args.results_dir,
        compile_check=args.compile,
        project_root=args.project_root,
        strict=args.strict,
    )
    print_report(report)
    if args.strict and not report["ok"]:
        sys.exit(1)
