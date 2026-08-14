#!/usr/bin/env python3
"""
环境检查脚本 — check_env.py
=============================
按特征动态验证 Python 依赖是否满足，输出 JSON 报告。
用法：python check_env.py --features data,optimization,machine-learning
"""

import importlib
import json
import sys
from typing import Dict, List, Tuple

# Windows 中文控制台默认 GBK，无法编码 ✓/✗ 等 Unicode 符号，统一转 UTF-8 输出避免崩溃
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

FEATURES: Dict[str, List[Tuple[str, str]]] = {
    "data": [
        ("pandas", "pandas"),
        ("numpy", "numpy"),
    ],
    "visualization": [
        ("matplotlib", "matplotlib"),
        ("seaborn", "seaborn"),
    ],
    "excel": [
        ("openpyxl", "openpyxl"),
        ("xlrd", "xlrd"),
    ],
    "optimization": [
        ("scipy", "scipy"),
    ],
    "integer-optimization": [
        ("pulp", "pulp"),
    ],
    "statistics": [
        ("statsmodels", "statsmodels"),
    ],
    "machine-learning": [
        ("sklearn", "scikit-learn"),
    ],
    "time-series": [
        ("statsmodels", "statsmodels"),
    ],
    "graph": [
        ("networkx", "networkx"),
    ],
    "image": [
        ("PIL", "Pillow"),
    ],
    "deep-learning": [
        ("tensorflow", "tensorflow"),
    ],
    "genetic-algorithm": [
        ("geatpy", "geatpy"),
    ],
}


def check_feature(feature: str) -> Dict:
    """检查单个 feature 的依赖是否可用。"""
    modules = FEATURES.get(feature, [])
    results = []
    all_ok = True
    for mod_name, pkg_name in modules:
        try:
            importlib.import_module(mod_name)
            results.append({"module": mod_name, "package": pkg_name, "status": "OK"})
        except ImportError:
            all_ok = False
            results.append({"module": mod_name, "package": pkg_name, "status": "MISSING"})
    return {"feature": feature, "ok": all_ok, "modules": results}


def check_env(features: List[str]) -> Dict:
    """检查一组 feature 的依赖。"""
    results = {}
    passed = []
    failed = []
    for feat in features:
        if feat not in FEATURES:
            results[feat] = {"feature": feat, "ok": False, "modules": [],
                             "error": f"未知 feature: {feat}"}
            failed.append(feat)
            continue
        r = check_feature(feat)
        results[feat] = r
        if r["ok"]:
            passed.append(feat)
        else:
            failed.append(feat)

    return {
        "requested_features": features,
        "all_passed": len(failed) == 0,
        "passed": passed,
        "failed": failed,
        "details": results,
    }


def list_features():
    """列出所有已知 feature。"""
    print("可用 feature 列表：")
    for feat, deps in FEATURES.items():
        pkgs = ", ".join(pkg for _, pkg in deps)
        print(f"  {feat:25s} → {pkgs}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="按特征检查 Python 环境依赖",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python check_env.py --features data,visualization\n"
               "  python check_env.py --features optimization,statistics,machine-learning\n"
               "  python check_env.py --list",
    )
    parser.add_argument("--features", type=str, default="",
                        help="逗号分隔的 feature 列表")
    parser.add_argument("--list", action="store_true",
                        help="列出所有可用 feature")
    parser.add_argument("--json", action="store_true",
                        help="以 JSON 格式输出报告")
    args = parser.parse_args()

    if args.list:
        list_features()
        sys.exit(0)

    if not args.features:
        # 未指定时检查全部
        requested = list(FEATURES.keys())
    else:
        requested = [f.strip() for f in args.features.split(",") if f.strip()]

    report = check_env(requested)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=" * 55)
        print("数学建模环境检查报告")
        print("=" * 55)
        for feat in requested:
            r = report["details"].get(feat, {})
            status_icon = "PASS" if r.get("ok") else "FAIL"
            print(f"\n[{status_icon}] {feat}")
            if "error" in r:
                print(f"  错误: {r['error']}")
            for mod in r.get("modules", []):
                icon = "  ✓" if mod["status"] == "OK" else "  ✗"
                print(f"  {icon} {mod['module']} ({mod['package']})")

        print("\n" + "-" * 55)
        passed = report["passed"]
        failed = report["failed"]
        print(f"通过: {len(passed)}/{len(requested)}")
        if failed:
            print(f"未通过: {', '.join(failed)}")
            print("\n请安装缺失的依赖：")
            print("  pip install -r requirements.txt")
        else:
            print("全部通过！环境就绪。")
        print("-" * 55)

    sys.exit(0 if report["all_passed"] else 1)
