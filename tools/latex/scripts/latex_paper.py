#!/usr/bin/env python3
"""
LaTeX 论文工程管理 — latex_paper.py
=====================================
轻量级 LaTeX 项目初始化、编译和校验工具。

用法：
  doctor   python tools/latex/scripts/latex_paper.py doctor
  init     python tools/latex/scripts/latex_paper.py init --output ./paper_project
  build    python tools/latex/scripts/latex_paper.py build --project ./paper_project
  validate python tools/latex/scripts/latex_paper.py validate --project ./paper_project --pdf ./paper_project/main.pdf
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ── 配置 ─────────────────────────────────────────────────────

TEMPLATE_TEX = Path(__file__).resolve().parents[3] / "template" / "paper.tex"

QUALITY_TARGETS = {
    "cumcm": {
        "min_pages": 6,       # 建议最少 6 页正文
        "max_pages": 30,      # 官方正文上限
        "min_equations": 5,
        "min_figures": 8,
        "min_tables": 3,
        "abstract_max_pages": 1,
    },
}


# ── doctor: 检查工具链 ──────────────────────────────────────

def doctor():
    """检查 LaTeX 编译工具链是否可用。"""
    results = {}

    # 检查 xelatex
    try:
        r = subprocess.run(["xelatex", "--version"], capture_output=True, timeout=10)
        results["xelatex"] = r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        results["xelatex"] = False

    # 检查 latexmk
    try:
        r = subprocess.run(["latexmk", "--version"], capture_output=True, timeout=10)
        results["latexmk"] = r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        results["latexmk"] = False

    # 检查 bibtex
    try:
        r = subprocess.run(["bibtex", "--version"], capture_output=True, timeout=10)
        results["bibtex"] = r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        results["bibtex"] = False

    return results


def print_doctor(results: dict):
    """打印工具链检查结果。"""
    print("=" * 45)
    print("LaTeX 工具链检查")
    print("=" * 45)
    for tool, ok in results.items():
        icon = "PASS" if ok else "MISSING"
        print(f"  [{icon}] {tool}")
    print("-" * 45)
    all_ok = all(results.values())
    if all_ok:
        print("全部就绪。推荐使用: latexmk -xelatex")
    else:
        missing = [k for k, v in results.items() if not v]
        print(f"缺失: {', '.join(missing)}")
        print("安装建议:")
        if "xelatex" in missing:
            print("  - Windows: 安装 MiKTeX 或 TeX Live")
            print("  - macOS: brew install --cask mactex")
            print("  - Linux: sudo apt install texlive-xetex")
        if "latexmk" in missing:
            print("  - TeX Live 通常自带 latexmk")
    print("=" * 45)
    return all_ok


# ── init: 初始化论文工程 ────────────────────────────────────

def init_project(output_dir: str, contest: str = "cumcm") -> str:
    """从模板初始化 LaTeX 论文工程目录。

    Parameters
    ----------
    output_dir : str
        输出目录路径。
    contest : str
        比赛类型（cumcm/mcm-icm）。

    Returns
    -------
    project_dir : str
    """
    project_dir = Path(output_dir).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)

    # 复制主模板
    if TEMPLATE_TEX.exists():
        shutil.copy2(TEMPLATE_TEX, project_dir / "main.tex")
    else:
        print(f"警告: 模板文件不存在 {TEMPLATE_TEX}")
        (project_dir / "main.tex").write_text(
            r"\documentclass[12pt,a4paper]{ctexart}" + "\n" +
            r"\begin{document}" + "\n" +
            r"论文内容" + "\n" +
            r"\end{document}" + "\n",
            encoding="utf-8",
        )

    # 复制参考文献模板
    bib_template = TEMPLATE_TEX.parent / "references.bib"
    if bib_template.exists():
        shutil.copy2(bib_template, project_dir / "references.bib")
    else:
        (project_dir / "references.bib").write_text(
            "% 参考文献\n", encoding="utf-8"
        )

    # 创建 figures 符号链接或目录
    figures_src = project_dir.parent / "figures"
    figures_dst = project_dir / "figures"
    if figures_src.exists() and not figures_dst.exists():
        try:
            # 尝试创建符号链接（Windows 可能需要管理员权限）
            figures_dst.symlink_to(figures_src.resolve())
        except OSError:
            # 回退：创建目录并复制
            figures_dst.mkdir(exist_ok=True)

    # 写入工程清单
    manifest = {
        "contest": contest,
        "template_source": str(TEMPLATE_TEX),
        "quality_targets": QUALITY_TARGETS.get(contest, QUALITY_TARGETS["cumcm"]),
    }
    import json
    (project_dir / "latex-project.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"论文工程已初始化: {project_dir}")
    print(f"  main.tex — 主文件")
    print(f"  references.bib — 参考文献")
    return str(project_dir)


# ── build: 编译 ──────────────────────────────────────────────

def build_paper(project_dir: str, engine: str = "latexmk", clean: bool = True) -> dict:
    """编译 LaTeX 工程。

    Parameters
    ----------
    project_dir : str
        论文工程目录（含 main.tex）。
    engine : str
        编译引擎：latexmk / xelatex。
    clean : bool
        是否清理辅助文件。

    Returns
    -------
    dict with keys: success, pdf_path, log, warnings
    """
    project = Path(project_dir).resolve()
    tex_file = project / "main.tex"
    if not tex_file.exists():
        return {"success": False, "error": f"main.tex 不存在: {tex_file}"}

    work_dir = str(project)
    log_lines = []
    warnings = []
    pdf = project / "main.pdf"

    try:
        if engine == "latexmk":
            # 首选 latexmk
            cmd = [
                "latexmk", "-xelatex", "-interaction=nonstopmode",
                "-halt-on-error", "-file-line-error",
                f"-output-directory={work_dir}", str(tex_file),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True,
                              cwd=work_dir, timeout=120)
            log_lines = r.stdout.splitlines() + r.stderr.splitlines()
            # 提取警告
            for line in log_lines:
                if "Warning" in line:
                    warnings.append(line.strip())

        elif engine == "xelatex":
            # 回退：xelatex + bibtex + xelatex*2
            for _ in range(2):
                r = subprocess.run(
                    ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
                     str(tex_file)],
                    capture_output=True, text=True, cwd=work_dir, timeout=60,
                )
                log_lines += r.stdout.splitlines()
                for line in r.stdout.splitlines():
                    if "Warning" in line:
                        warnings.append(line.strip())
                # bibtex
                aux = project / "main.aux"
                if aux.exists():
                    subprocess.run(["bibtex", "main"], capture_output=True,
                                  cwd=work_dir, timeout=30)

        success = pdf.exists() and pdf.stat().st_size > 1000

        # 清理
        if clean and success:
            for ext in [".aux", ".log", ".out", ".toc", ".bbl", ".blg", ".synctex.gz",
                        ".fdb_latexmk", ".fls", ".xdv"]:
                for f in project.glob(f"*{ext}"):
                    try:
                        f.unlink()
                    except OSError:
                        pass

    except subprocess.TimeoutExpired:
        success = False
        warnings.append("编译超时（超过 120 秒）")
    except FileNotFoundError:
        return {"success": False, "error": f"引擎 {engine} 不可用，请先运行 doctor"}

    return {
        "success": success,
        "pdf_path": str(pdf) if success else None,
        "warnings": warnings[:20],
    }


# ── validate: 校验 ───────────────────────────────────────────

def validate_paper(project_dir: str, pdf_path: str = None,
                   contest: str = "cumcm") -> dict:
    """校验编译后的论文。

    Parameters
    ----------
    project_dir : str
        论文工程目录。
    pdf_path : str
        编译生成的 PDF 路径。
    contest : str
        比赛类型。

    Returns
    -------
    dict with keys: ok, issues, warnings, stats
    """
    project = Path(project_dir).resolve()
    tex_file = project / "main.tex"
    # 如果模板目录中文件叫 paper.tex，自动识别
    if not tex_file.exists():
        tex_file = project / "paper.tex"
    issues = []
    w = []
    stats = {"equations": 0, "figures": 0, "tables": 0, "pages_estimate": 0}
    targets = QUALITY_TARGETS.get(contest, QUALITY_TARGETS["cumcm"])

    if not tex_file.exists():
        return {"ok": False, "issues": ["main.tex（或 paper.tex）不存在"],
                "warnings": [], "stats": stats, "targets": targets}

    tex_content = tex_file.read_text(encoding="utf-8", errors="replace")

    # 统计公式（\begin{equation} 或 $$）
    stats["equations"] = len(re.findall(r'\\begin\{equation\}', tex_content)) + \
                         len(re.findall(r'(?<!\\)\$\$(.+?)(?<!\\)\$\$', tex_content, re.DOTALL))

    # 统计图表
    stats["figures"] = len(re.findall(r'\\includegraphics', tex_content))
    stats["tables"] = len(re.findall(r'\\begin\{tabular\}', tex_content)) + \
                      len(re.findall(r'\\begin\{table\}', tex_content))

    # 页码估计（粗略：每 2500 字符 ≈ 1 页）
    chars = len(tex_content)
    stats["pages_estimate"] = max(1, chars // 2500)

    # 校验
    targets = QUALITY_TARGETS.get(contest, QUALITY_TARGETS["cumcm"])

    if stats["equations"] < targets["min_equations"]:
        w.append(f"公式数量: {stats['equations']} < {targets['min_equations']}（建议）")
    if stats["figures"] < targets["min_figures"]:
        w.append(f"图表数量: {stats['figures']} < {targets['min_figures']}（建议）")
    if stats["tables"] < targets["min_tables"]:
        w.append(f"表格数量: {stats['tables']} < {targets['min_tables']}（建议）")
    if stats["pages_estimate"] > targets["max_pages"]:
        issues.append(f"正文估计 {stats['pages_estimate']} 页 > {targets['max_pages']} 页上限")

    # 检查常见问题
    if "??" in tex_content:
        issues.append("存在未解析的引用（?? 标记）")
    if r"\begin{figure}" in tex_content and r"\caption" not in tex_content:
        w.append("部分图表缺少标题（\\caption）")
    if r"\cite{" in tex_content and not (project / "references.bib").exists():
        w.append("引用了文献但没有 references.bib 文件")

    ok = len(issues) == 0

    return {
        "ok": ok,
        "issues": issues,
        "warnings": w,
        "stats": stats,
        "targets": targets,
    }


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="LaTeX 论文工程管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python latex_paper.py doctor
  python latex_paper.py init --output ./my_paper
  python latex_paper.py build --project ./my_paper
  python latex_paper.py validate --project ./my_paper --pdf ./my_paper/main.pdf""",
    )
    sub = parser.add_subparsers(dest="command")

    p_doctor = sub.add_parser("doctor", help="检查 LaTeX 工具链")

    p_init = sub.add_parser("init", help="初始化论文工程")
    p_init.add_argument("--output", default="./paper_project",
                        help="输出目录（默认 ./paper_project）")
    p_init.add_argument("--contest", default="cumcm",
                        help="比赛类型（cumcm/mcm-icm）")

    p_build = sub.add_parser("build", help="编译论文")
    p_build.add_argument("--project", default="./paper_project",
                         help="论文工程目录")
    p_build.add_argument("--engine", default="latexmk",
                         help="编译引擎（latexmk/xelatex）")

    p_val = sub.add_parser("validate", help="校验论文")
    p_val.add_argument("--project", default="./paper_project",
                       help="论文工程目录")
    p_val.add_argument("--pdf", default=None, help="PDF 路径")
    p_val.add_argument("--contest", default="cumcm",
                       help="比赛类型")

    args = parser.parse_args()

    if args.command == "doctor":
        result = doctor()
        print_doctor(result)
        sys.exit(0 if all(result.values()) else 1)

    elif args.command == "init":
        init_project(args.output, args.contest)

    elif args.command == "build":
        result = build_paper(args.project, args.engine)
        if result["success"]:
            print(f"编译成功: {result['pdf_path']}")
            if result["warnings"]:
                print(f"警告 ({len(result['warnings'])}):")
                for w in result["warnings"][:5]:
                    print(f"  - {w}")
        else:
            print(f"编译失败: {result.get('error', '未知错误')}")
            sys.exit(1)

    elif args.command == "validate":
        result = validate_paper(args.project, args.pdf, args.contest)
        print("=" * 45)
        print("论文校验报告")
        print("=" * 45)
        print(f"公式: {result['stats']['equations']} "
              f"(建议≥{result['targets']['min_equations']})")
        print(f"图表: {result['stats']['figures']} "
              f"(建议≥{result['targets']['min_figures']})")
        print(f"表格: {result['stats']['tables']} "
              f"(建议≥{result['targets']['min_tables']})")
        print(f"估计页数: {result['stats']['pages_estimate']} "
              f"(上限{result['targets']['max_pages']})")

        if result["issues"]:
            print(f"\n问题 ({len(result['issues'])}):")
            for i, iss in enumerate(result["issues"], 1):
                print(f"  {i}. {iss}")
        if result["warnings"]:
            print(f"\n警告 ({len(result['warnings'])}):")
            for i, w in enumerate(result["warnings"], 1):
                print(f"  {i}. {w}")
        verdict = "PASS" if result["ok"] else "FAIL"
        print(f"\n{'─' * 45}")
        print(f"结果: {verdict}")
        print(f"{'─' * 45}")
        sys.exit(0 if result["ok"] else 1)

    else:
        parser.print_help()
