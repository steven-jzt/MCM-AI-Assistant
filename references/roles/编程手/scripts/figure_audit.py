#!/usr/bin/env python3
"""
图表审计脚本 — figure_audit.py
================================
检查 figures/ 目录中的图表是否符合出版级标准。
无外部依赖（仅标准库），可在任何 Python 3.8+ 环境运行。

用法：
  python figure_audit.py <figures_dir>        # 普通模式
  python figure_audit.py <figures_dir> --strict  # 严格模式（不通过则 exit 1）
"""

import os
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Windows 中文控制台默认 GBK，无法编码 ⚠ 等 Unicode 符号，统一转 UTF-8 输出避免崩溃
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


# ── PNG DPI 解析 ──────────────────────────────────────────────


def _png_metadata(filepath: str) -> dict:
    """从 PNG IHDR/pHYs chunk 提取元数据。"""
    info = {"width": 0, "height": 0, "dpi": 0, "physical_w_in": 0, "physical_h_in": 0}
    try:
        with open(filepath, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                return info
            while True:
                length_bytes = f.read(4)
                if not length_bytes:
                    break
                length = struct.unpack(">I", length_bytes)[0]
                chunk_type = f.read(4)
                data = f.read(length)
                f.read(4)  # CRC

                if chunk_type == b"IHDR":
                    info["width"] = struct.unpack(">I", data[0:4])[0]
                    info["height"] = struct.unpack(">I", data[4:8])[0]
                elif chunk_type == b"pHYs":
                    ppu_x = struct.unpack(">I", data[0:4])[0]
                    ppu_y = struct.unpack(">I", data[4:8])[0]
                    unit = data[8]
                    if unit == 1:  # 像素/米
                        info["dpi"] = round(ppu_x * 0.0254)
                        info["physical_w_in"] = info["width"] / ppu_x * 39.3701
                        info["physical_h_in"] = info["height"] / ppu_y * 39.3701
    except Exception:
        pass
    return info


# ── SVG 元数据 ──────────────────────────────────────────────────


def _svg_metadata(filepath: str) -> dict:
    """从 SVG 提取文本节点数量和嵌入栅格图数量。"""
    info = {"text_count": 0, "embedded_rasters": 0}
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        ns = {"svg": "http://www.w3.org/2000/svg"}
        texts = root.findall(".//svg:text", ns) + root.findall(".//{http://www.w3.org/2000/svg}text")
        info["text_count"] = len(texts)
        images = root.findall(".//svg:image", ns) + root.findall(".//{http://www.w3.org/2000/svg}image")
        info["embedded_rasters"] = len(images)
    except Exception:
        pass
    return info


# ── 目录审计 ─────────────────────────────────────────────────────


def audit_figure_directory(figures_dir: str, strict: bool = False) -> dict:
    """
    审计 figures/ 目录。

    Returns
    -------
    dict with keys: png_files, svg_files, jpeg_files, unmatched_png, unmatched_svg,
                    low_dpi, categories, issues, ok
    """
    p = Path(figures_dir)
    if not p.is_dir():
        return {
            "ok": False,
            "directory": str(p.resolve()),
            "png_count": 0,
            "svg_count": 0,
            "jpeg_count": 0,
            "unmatched_png": [],
            "unmatched_svg": [],
            "low_dpi": [],
            "categories": {"raw": 0, "process": 0, "result": 0, "other": 0},
            "category_files": {"raw": [], "process": [], "result": [], "other": []},
            "issues": [f"目录不存在: {figures_dir}"],
            "warnings": [],
        }

    png_files = sorted(p.glob("*.png"))
    svg_files = sorted(p.glob("*.svg"))
    jpeg_files = sorted(list(p.glob("*.jpg")) + list(p.glob("*.jpeg")))

    png_stems = {f.stem for f in png_files}
    svg_stems = {f.stem for f in svg_files}

    unmatched_png = png_stems - svg_stems
    unmatched_svg = svg_stems - png_stems

    issues = []
    warnings = []

    # 1. JPEG 禁用
    if jpeg_files:
        issues.append(f"发现 {len(jpeg_files)} 个 JPEG 文件（禁止使用）: "
                      f"{[f.name for f in jpeg_files]}")

    # 2. DPI 检查
    low_dpi = []
    for f in png_files:
        meta = _png_metadata(str(f))
        dpi = meta["dpi"]
        if dpi > 0 and dpi < 300:
            low_dpi.append((f.name, dpi))
    if low_dpi:
        issues.append(f"低 DPI 图片: {[(n, d) for n, d in low_dpi]}")

    # 3. SVG/PNG 配对
    if unmatched_png:
        warnings.append(f"有 PNG 但无对应 SVG: {unmatched_png}")
    if unmatched_svg:
        warnings.append(f"有 SVG 但无对应 PNG: {unmatched_svg}")

    # 4. 图数量
    if len(png_files) < 9:
        warnings.append(f"PNG 图仅 {len(png_files)} 张（建议 ≥9）")

    # 5. 图片分类统计
    categories = {"raw": [], "process": [], "result": [], "other": []}
    for f in png_files:
        name = f.stem.lower()
        if name.startswith("raw_"):
            categories["raw"].append(f.name)
        elif name.startswith("process_"):
            categories["process"].append(f.name)
        elif name.startswith("result_"):
            categories["result"].append(f.name)
        else:
            categories["other"].append(f.name)

    for cat, files in categories.items():
        if cat != "other" and len(files) < 3:
            warnings.append(f"'{cat}_' 类图仅 {len(files)} 张（建议每类 ≥3）")

    # 6. 大文件警告（SVG 超过 2MB 可能含过多节点）
    for f in svg_files:
        size_kb = f.stat().st_size / 1024
        if size_kb > 2048:
            warnings.append(f"SVG 文件过大: {f.name} ({size_kb:.0f} KB)")

    ok = len(issues) == 0

    report = {
        "ok": ok,
        "directory": str(p.resolve()),
        "png_count": len(png_files),
        "svg_count": len(svg_files),
        "jpeg_count": len(jpeg_files),
        "unmatched_png": sorted(unmatched_png),
        "unmatched_svg": sorted(unmatched_svg),
        "low_dpi": low_dpi,
        "categories": {k: len(v) for k, v in categories.items()},
        "category_files": categories,
        "issues": issues,
        "warnings": warnings,
    }
    return report


def print_report(report: dict):
    """美观打印审计报告。"""
    print("=" * 55)
    print("图表审计报告")
    print("=" * 55)
    print(f"目录  : {report.get('directory', 'N/A')}")
    print(f"PNG   : {report['png_count']} 张")
    print(f"SVG   : {report['svg_count']} 张")
    print(f"JPEG  : {report['jpeg_count']} 张" + (" ⚠" if report['jpeg_count'] > 0 else ""))
    print(f"\n分类统计:")
    for cat, count in report.get("categories", {}).items():
        print(f"  {cat}: {count} 张")

    issues = report.get("issues", [])
    warnings = report.get("warnings", [])
    unmatched_png = report.get("unmatched_png", [])
    unmatched_svg = report.get("unmatched_svg", [])

    if unmatched_png or unmatched_svg:
        print(f"\n配对缺失:")
        if unmatched_png:
            print(f"  PNG→SVG 缺失: {unmatched_png}")
        if unmatched_svg:
            print(f"  SVG→PNG 缺失: {unmatched_svg}")

    if issues:
        print(f"\n问题 ({len(issues)}):")
        for i, iss in enumerate(issues, 1):
            print(f"  {i}. {iss}")

    if warnings:
        print(f"\n警告 ({len(warnings)}):")
        for i, w in enumerate(warnings, 1):
            print(f"  {i}. {w}")

    verdict = "PASS" if report["ok"] else "FAIL"
    print(f"\n{'─' * 55}")
    print(f"结果: {verdict}")
    print(f"{'─' * 55}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python figure_audit.py <figures_dir> [--strict]")
        sys.exit(1)

    target = sys.argv[1]
    strict = "--strict" in sys.argv
    report = audit_figure_directory(target, strict=strict)
    print_report(report)
    if strict and not report["ok"]:
        sys.exit(1)
