"""
数据加载工具 — data_loader.py
==============================
统一的文件读取接口，根据后缀自动识别格式。
支持 CSV / Excel / MATLAB / JSON / TXT。
"""

import os
from typing import Union, Dict, List, Any

import numpy as np
import pandas as pd


# ============================================================================
# 内部辅助
# ============================================================================

_SUPPORTED_EXTENSIONS = {
    ".csv": "CSV (逗号分隔值)",
    ".xls": "Excel 工作簿",
    ".xlsx": "Excel 工作簿",
    ".mat": "MATLAB 数据文件",
    ".json": "JSON 文件",
    ".txt": "纯文本文件",
}


def _check_file(filepath: str) -> str:
    """检查文件是否存在，返回归一化路径。"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    if not os.path.isfile(filepath):
        raise IsADirectoryError(f"路径是文件夹而非文件: {filepath}")
    return os.path.abspath(filepath)


# ============================================================================
# 1. 自动加载
# ============================================================================

def auto_load(filepath: str) -> Union[pd.DataFrame, dict, list, str]:
    """
    自动识别文件格式并加载数据。

    根据文件扩展名选择对应的解析器，一行代码完成数据读取。

    Parameters
    ----------
    filepath : str
        数据文件路径。

    Returns
    -------
    data : pd.DataFrame | dict | list | str
        - .csv  → pd.DataFrame
        - .xls / .xlsx → pd.DataFrame
        - .mat  → dict（仅包含不以 '__' 开头的变量）
        - .json → dict 或 list（取决于 JSON 顶层结构）
        - .txt  → str（原始文本内容）

    Raises
    ------
    FileNotFoundError
        文件不存在。
    ValueError
        文件格式不支持。
    ImportError
        读取 .mat 文件需要 scipy（`pip install scipy`）。

    Examples
    --------
    >>> df = auto_load("data/oscil.csv")
    >>> mat_vars = auto_load("data/signals.mat")
    """
    filepath = _check_file(filepath)
    ext = os.path.splitext(filepath)[1].lower()

    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"不支持的文件格式 '{ext}'。\n"
            f"当前支持: {', '.join(_SUPPORTED_EXTENSIONS.keys())}"
        )

    if ext == ".csv":
        try:
            return pd.read_csv(filepath)
        except UnicodeDecodeError:
            # 尝试常见中文编码
            for enc in ["gbk", "gb2312", "gb18030", "utf-8-sig"]:
                try:
                    return pd.read_csv(filepath, encoding=enc)
                except UnicodeDecodeError:
                    continue
            raise UnicodeDecodeError(
                "", b"", 0, 1,
                "无法以 utf-8 / gbk / gb2312 编码读取 CSV，请检查文件编码。"
            )

    elif ext in (".xls", ".xlsx"):
        try:
            return pd.read_excel(filepath, sheet_name=0)
        except Exception as e:
            raise ValueError(f"Excel 文件读取失败: {e}")

    elif ext == ".mat":
        try:
            from scipy.io import loadmat
        except ImportError:
            raise ImportError("读取 .mat 需要 scipy。请运行: pip install scipy")
        raw = loadmat(filepath)
        return {k: v for k, v in raw.items() if not k.startswith("__")}

    elif ext == ".json":
        import json
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    elif ext == ".txt":
        # 优先用 UTF-8，失败则尝试 GBK
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="gbk") as f:
                return f.read()

    # 兜底（不应到达）
    raise ValueError(f"未知格式: {ext}")


# ============================================================================
# 2. 列出 Excel 工作表
# ============================================================================

def list_sheets(filepath: str) -> List[str]:
    """
    列出 Excel 文件中所有工作表名称。

    Parameters
    ----------
    filepath : str
        Excel 文件路径 (.xls 或 .xlsx)。

    Returns
    -------
    sheets : list of str
        工作表名称列表。

    Raises
    ------
    FileNotFoundError
        文件不存在。
    ValueError
        文件不是 Excel 格式或读取失败。

    Examples
    --------
    >>> sheets = list_sheets("data/multi_sheet.xlsx")
    >>> print(sheets)
    ['Sheet1', 'Sheet2', '汇总']
    """
    filepath = _check_file(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".xls", ".xlsx"):
        raise ValueError(f"list_sheets 仅支持 .xls / .xlsx 文件，当前为 '{ext}'")

    try:
        xl = pd.ExcelFile(filepath)
        return xl.sheet_names
    except Exception as e:
        raise ValueError(f"读取 Excel 工作表列表失败: {e}")


# ============================================================================
# 3. 加载指定工作表
# ============================================================================

def load_sheet(filepath: str, sheet_name: Union[str, int] = 0) -> pd.DataFrame:
    """
    读取 Excel 文件的指定工作表。

    Parameters
    ----------
    filepath : str
        Excel 文件路径。
    sheet_name : str or int
        工作表名称（如 "Sheet1"）或索引（0 表示第一个）。默认 0。

    Returns
    -------
    df : pd.DataFrame
        指定工作表的数据框。

    Raises
    ------
    FileNotFoundError
        文件不存在。
    ValueError
        指定的工作表不存在或读取失败。

    Examples
    --------
    >>> df = load_sheet("data/survey.xlsx", sheet_name="汇总")
    >>> df = load_sheet("data/survey.xlsx", sheet_name=2)
    """
    filepath = _check_file(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".xls", ".xlsx"):
        raise ValueError(f"load_sheet 仅支持 .xls / .xlsx 文件，当前为 '{ext}'")

    try:
        return pd.read_excel(filepath, sheet_name=sheet_name)
    except ValueError as e:
        # 可能是 sheet_name 不存在
        available = list_sheets(filepath)
        raise ValueError(
            f"工作表 '{sheet_name}' 不存在。\n"
            f"当前文件包含以下工作表: {available}"
        )
    except Exception as e:
        raise ValueError(f"读取工作表失败: {e}")


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    import tempfile
    import json

    np.set_printoptions(precision=2, suppress=True)

    print("=" * 60)
    print("数据加载工具 — 测试示例")
    print("=" * 60)

    tmp_dir = tempfile.mkdtemp(prefix="data_loader_test_")
    print(f"\n临时目录: {tmp_dir}")

    # ---- 创建临时测试文件 ----
    test_files = {}

    # 1) CSV
    csv_path = os.path.join(tmp_dir, "test.csv")
    df_csv = pd.DataFrame({
        "城市": ["北京", "上海", "广州"],
        "GDP": [40000, 44000, 28000],
        "人口": [2154, 2487, 1867],
    })
    df_csv.to_csv(csv_path, index=False, encoding="utf-8-sig")
    test_files[".csv"] = csv_path

    # 2) Excel (含两个 sheet)
    xlsx_path = os.path.join(tmp_dir, "test.xlsx")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df_csv.to_excel(writer, sheet_name="城市数据", index=False)
        pd.DataFrame({
            "指标": ["GDP", "人口"],
            "权重": [0.6, 0.4],
        }).to_excel(writer, sheet_name="权重表", index=False)
    test_files[".xlsx"] = xlsx_path

    # 3) JSON
    json_path = os.path.join(tmp_dir, "test.json")
    config = {"name": "模型参数", "alpha": 0.05, "samples": 100}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False)
    test_files[".json"] = json_path

    # 4) TXT
    txt_path = os.path.join(tmp_dir, "test.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("这是一段文本数据。\n第二行。")
    test_files[".txt"] = txt_path

    # ---- 测试 auto_load ----
    print("\n" + "-" * 40)
    print("[1] auto_load — 自动识别格式")
    print("-" * 40)

    for ext, path in test_files.items():
        try:
            data = auto_load(path)
            if isinstance(data, pd.DataFrame):
                print(f"  {ext}: DataFrame {data.shape} — 列: {list(data.columns)}")
            elif isinstance(data, dict):
                print(f"  {ext}: dict — 键: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"  {ext}: list — 长度: {len(data)}")
            elif isinstance(data, str):
                preview = data[:40].replace("\n", "\\n")
                print(f"  {ext}: str — 预览: \"{preview}...\"")
        except Exception as e:
            print(f"  {ext}: 失败 — {e}")

    # ---- 测试 list_sheets / load_sheet ----
    print("\n" + "-" * 40)
    print("[2] list_sheets & load_sheet — Excel 多工作表")
    print("-" * 40)

    try:
        sheets = list_sheets(xlsx_path)
        print(f"  工作表列表: {sheets}")

        for s in sheets:
            df = load_sheet(xlsx_path, sheet_name=s)
            print(f"  [{s}] {df.shape} — 列: {list(df.columns)}")
    except Exception as e:
        print(f"  失败: {e}")

    # ---- 异常测试 ----
    print("\n" + "-" * 40)
    print("[3] 异常处理测试")
    print("-" * 40)

    # 不存在文件
    try:
        auto_load("/不存在的文件.csv")
    except FileNotFoundError as e:
        print(f"  文件不存在: {e}")

    # 不支持格式（需要真实文件才能通过 _check_file）
    fake_path = os.path.join(tmp_dir, "test.xyz")
    with open(fake_path, "w") as f:
        f.write("dummy")
    try:
        auto_load(fake_path)
    except ValueError as e:
        print(f"  不支持格式: {e}")

    # Excel sheet 不存在
    try:
        load_sheet(xlsx_path, sheet_name="不存在的工作表")
    except ValueError as e:
        print(f"  Sheet 不存在: {e}")

    # ---- 清理 ----
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print(f"测试完成（已清理临时目录）")
    print(f"支持格式: {', '.join(_SUPPORTED_EXTENSIONS.keys())}")
    print("=" * 60)
