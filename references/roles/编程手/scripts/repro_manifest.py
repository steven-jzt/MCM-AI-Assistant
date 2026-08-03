#!/usr/bin/env python3
"""
复现清单生成器 — repro_manifest.py
=====================================
生成可复现性清单 JSON 文件，记录随机种子、输入文件哈希、运行时环境与复现命令。

用法：
  python repro_manifest.py --output results/复现清单.json \
      --seed 42 --inputs data/*.csv --command "python code/main.py"
"""

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCHEMA_VERSION = 1


def sha256_file(filepath: str) -> str:
    """计算文件的 SHA-256 哈希。"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def scan_inputs(patterns_or_paths: list) -> list:
    """扫描输入文件列表，返回路径/SHA-256/字节数信息。"""
    result = []
    seen = set()
    for item in patterns_or_paths:
        p = Path(item)
        if p.is_file():
            if str(p.resolve()) not in seen:
                seen.add(str(p.resolve()))
                result.append({
                    "path": str(p),
                    "sha256": sha256_file(str(p)),
                    "bytes": p.stat().st_size,
                })
        elif p.is_dir():
            for f in sorted(p.iterdir()):
                if f.is_file() and str(f.resolve()) not in seen:
                    seen.add(str(f.resolve()))
                    result.append({
                        "path": str(f),
                        "sha256": sha256_file(str(f)),
                        "bytes": f.stat().st_size,
                    })
    return result


def get_dependencies() -> dict:
    """获取关键依赖的版本信息。"""
    deps = {}
    for pkg in ["numpy", "pandas", "scipy", "matplotlib", "seaborn",
                "scikit-learn", "statsmodels"]:
        try:
            mod = __import__(pkg)
            deps[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            deps[pkg] = None
    return deps


def build_manifest(
    seed: int = 42,
    inputs: list = None,
    reproduce_command: str = "python code/main.py",
    output_path: str = "results/复现清单.json",
    key_params: dict = None,
) -> dict:
    """构建复现清单。

    Parameters
    ----------
    seed : int
        全局随机种子。
    inputs : list of str
        输入文件的路径或 glob 模式列表。
    reproduce_command : str
        一键复现命令。
    output_path : str
        清单保存路径。
    key_params : dict
        关键参数（如 train/test 比例、k-fold 值等）。
    """
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "random_seed": seed,
        "input_files": scan_inputs(inputs or []),
        "runtime": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
        },
        "dependencies": get_dependencies(),
        "key_parameters": key_params or {},
        "reproduce_command": reproduce_command,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 安全检查：拒绝写入到项目根外的路径
    cwd = Path.cwd().resolve()
    if not str(out.resolve()).startswith(str(cwd)):
        raise ValueError(f"输出路径必须在项目目录内: {output_path}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"复现清单已保存至: {output_path}")
    print(f"  Schema 版本: {SCHEMA_VERSION}")
    print(f"  随机种子: {seed}")
    print(f"  输入文件数: {len(manifest['input_files'])}")
    print(f"  复现命令: {reproduce_command}")

    return manifest


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="生成数学建模结果的复现清单",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               '  python repro_manifest.py --output results/复现清单.json \\\n'
               '      --seed 42 --inputs data/附件1.csv data/附件2.xlsx \\\n'
               '      --command "python code/main.py"\n'
               '  python repro_manifest.py --output results/复现清单.json \\\n'
               '      --seed 42 --inputs data/ --key-params \'{"split":0.8,"kfold":5}\'',
    )
    parser.add_argument("--output", type=str, default="results/复现清单.json",
                        help="输出 JSON 文件路径")
    parser.add_argument("--seed", type=int, default=42,
                        help="全局随机种子")
    parser.add_argument("--inputs", type=str, nargs="*", default=None,
                        help="输入文件/目录列表")
    parser.add_argument("--command", type=str, default="python code/main.py",
                        help="一键复现命令")
    parser.add_argument("--key-params", type=str, default=None,
                        help="关键参数 JSON 字符串")
    args = parser.parse_args()

    key_params = {}
    if args.key_params:
        key_params = json.loads(args.key_params)

    build_manifest(
        seed=args.seed,
        inputs=args.inputs,
        reproduce_command=args.command,
        output_path=args.output,
        key_params=key_params,
    )
