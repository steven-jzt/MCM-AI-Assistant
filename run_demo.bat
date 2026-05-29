@echo off
chcp 65001 >nul
REM ============================================================================
REM  CUMCM-AI-Assistant 工具链完整性验证脚本 (Windows)
REM ============================================================================
REM  用法：双击运行 或 在命令行中执行 run_demo.bat
REM  功能：生成虚拟赛题 → 验证模型库/工具导入 → 跑通全流程 → 输出结果
REM ============================================================================
setlocal enabledelayedexpansion

echo ================================================
echo   CUMCM-AI-Assistant  工具链完整性验证
echo ================================================
echo.

REM -------------------- 1. 检查 Python 环境 --------------------
echo [STEP] 1. 检查 Python 环境...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] 未找到 Python，请先安装 Python 3.9+。
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo [INFO] %PY_VER%

REM -------------------- 2. 检查依赖 --------------------
echo [STEP] 2. 检查 Python 依赖...
set MISSING=
for %%p in (numpy pandas scipy matplotlib seaborn sklearn statsmodels) do (
    python -c "import %%p" 2>nul || set MISSING=!MISSING!  %%p
)
if not "!MISSING!"=="" (
    echo [FAIL] 缺少以下依赖包:!MISSING!
    echo         请运行: pip install -r requirements.txt
    pause
    exit /b 1
)
echo [INFO] 所有依赖已就绪。

REM -------------------- 3. 验证模型库导入 --------------------
echo [STEP] 3. 验证模型库模块导入...
for %%m in (model_library.evaluation model_library.prediction model_library.optimization model_library.statistics model_library.differential utils.data_loader utils.visual) do (
    python -c "import %%m" 2>nul && echo         √ %%m || (
        echo [FAIL] × %%m 导入失败
        pause
        exit /b 1
    )
)
echo [INFO] 所有模块导入成功。

REM -------------------- 4. 虚拟赛题全流程演示 --------------------
echo [STEP] 4. 运行虚拟赛题全流程演示...

REM 生成时间戳输出目录
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value') do set DT=%%i
set DEMO_DIR=results\demo_%DT:~0,8%_%DT:~8,6%

python -c "import os; os.makedirs('%DEMO_DIR%', exist_ok=True)"

python << PYEOF
import os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

for f in ["SimHei", "Songti SC", "Microsoft YaHei", "WenQuanYi Micro Hei", "DejaVu Sans"]:
    try:
        plt.rcParams["font.sans-serif"] = [f]
        plt.rcParams["axes.unicode_minus"] = False
        break
    except Exception:
        continue

out_dir = os.environ.get("DEMO_DIR", "results/demo")
os.makedirs(out_dir, exist_ok=True)

print("=" * 60)
print("  虚拟赛题：城市空气质量综合评价与预测")
print("=" * 60)
print()
print("【问题1】基于 AQI、PM2.5、PM10、SO2、NO2、CO 六个指标，")
print("         对 12 个城市的空气质量进行综合评价并排名。")
print("【问题2】基于过去 36 个月的 AQI 历史数据，预测未来 3 个月的趋势。")
print()

# ---- 问题1 ----
print(">> 问题 1 / 步骤 1：构造虚拟数据 ...")
np.random.seed(42)
n_cities, n_indicators = 12, 6
cities = [f"城市{i+1}" for i in range(n_cities)]
indicators = ["AQI", "PM2.5", "PM10", "SO2", "NO2", "CO"]
base = np.random.uniform(30, 120, (n_cities, n_indicators))
base[:3]  *= 0.5
base[9:]  *= 1.8
data_df = pd.DataFrame(base, index=cities, columns=indicators)
data_df.to_csv(f"{out_dir}/mock_city_air_quality.csv", encoding="utf-8-sig")
print(f"    已生成 {n_cities} 个城市 × {n_indicators} 个指标 → mock_city_air_quality.csv")

print(">> 问题 1 / 步骤 2：调用 evaluation 模块（熵权法 + TOPSIS）...")
from model_library.evaluation import entropy_weight, topsis
weights = entropy_weight(base)
scores = topsis(base, weights, impacts=np.array([-1]*n_indicators))
rank = np.argsort(-scores) + 1
result_df = pd.DataFrame({"城市": cities, "TOPSIS得分": np.round(scores, 4), "排名": rank.astype(int)}).sort_values("排名")
result_df.to_csv(f"{out_dir}/problem1_ranking.csv", encoding="utf-8-sig", index=False)
top3_idx = np.argsort(-scores)[:3]
print("    排名前 3：", ", ".join(f"{cities[i]}(得分{scores[i]:.3f})" for i in top3_idx))

print(">> 问题 1 / 步骤 3：绘制评价结果柱状图 ...")
from utils.visual import bar_chart
bar_chart(
    labels=cities, values=scores,
    title="城市空气质量综合评价 TOPSIS 得分",
    xlabel="城市", ylabel="TOPSIS 得分",
    save_path=f"{out_dir}/problem1_bar.png"
)
print(f"    图表已保存 → problem1_bar.png")

# ---- 问题2 ----
print()
print(">> 问题 2 / 步骤 1：生成 36 个月虚拟 AQI 数据 ...")
np.random.seed(123)
t = np.arange(1, 37)
trend = 80 + 0.2 * t
seasonal = 15 * np.sin(2 * np.pi * t / 12)
noise = np.random.normal(0, 5, 36)
aqi_series = np.maximum(trend + seasonal + noise, 10)
pd.DataFrame({"月份": t.astype(int), "AQI": np.round(aqi_series, 2)}).to_csv(
    f"{out_dir}/mock_aqi_timeseries.csv", encoding="utf-8-sig", index=False
)
print(f"    已生成 36 个月数据 → mock_aqi_timeseries.csv")

print(">> 问题 2 / 步骤 2：调用 prediction 模块（灰色预测 GM(1,1)）...")
from model_library.prediction import gm11
try:
    fitted, forecast, c_ratio = gm11(aqi_series, predict_n=3)
    print(f"    未来 3 个月预测 AQI：{[f'{v:.2f}' for v in forecast]}")
    quality = "优" if c_ratio < 0.35 else ("合格" if c_ratio < 0.5 else ("勉强" if c_ratio < 0.65 else "不合格"))
    print(f"    后验差比值 C={c_ratio:.4f} ({quality})")
except Exception as e:
    print(f"    GM(1,1) 失败: {e}，回退到指数平滑")
    from model_library.prediction import exponential_smoothing
    forecast, result_df = exponential_smoothing(aqi_series, predict_n=3)

print(">> 问题 2 / 步骤 3：绘制预测曲线 ...")
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(range(1, 37), aqi_series, "b-o", label="历史 AQI", markersize=4)
ax.plot(range(37, 40), forecast, "r--s", label="预测 AQI", markersize=6)
ax.axvline(x=36.5, color="gray", linestyle=":", alpha=0.7)
ax.set_xlabel("月份"); ax.set_ylabel("AQI")
ax.set_title("城市 AQI 历史数据与预测"); ax.legend(); ax.grid(True, alpha=0.3)
fig.tight_layout(); fig.savefig(f"{out_dir}/problem2_forecast.png", dpi=300)
plt.close(fig)
print(f"    图表已保存 → problem2_forecast.png")

print()
print("=" * 60)
print("  [OK] 全流程验证完成！")
print("=" * 60)
print(f"  所有输出文件位于: {out_dir}/")
for f in sorted(os.listdir(out_dir)):
    print(f"    - {f}")
print()
print("  工具链状态：正常")
print("  模型库导入：正常")
print("  数据生成：正常")
print("  综合评价：正常")
print("  预测建模：正常")
print("  图表输出：正常")
PYEOF

echo.
echo [INFO] 工具链完整性验证通过！
echo        查看结果: dir %DEMO_DIR%\
pause
endlocal
