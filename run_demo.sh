#!/usr/bin/env bash
# ============================================================================
#  CUMCM-AI-Assistant 工具链完整性验证脚本 (macOS / Linux)
# ============================================================================
#  用法：bash run_demo.sh
#  功能：生成虚拟赛题 → 验证模型库/工具导入 → 跑通全流程 → 输出结果
# ============================================================================
set -e

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

echo_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
echo_step()  { echo -e "${YELLOW}[STEP]${NC}  $1"; }
echo_fail()  { echo -e "${RED}[FAIL]${NC}  $1"; }

echo "================================================"
echo "  CUMCM-AI-Assistant  工具链完整性验证"
echo "================================================"
echo ""

# -------------------- 1. 检查 Python 环境 --------------------
echo_step "1. 检查 Python 环境..."
PYTHON=$(which python 2>/dev/null || which python3 2>/dev/null)
if [ -z "$PYTHON" ]; then
    echo_fail "未找到 Python，请先安装 Python 3.9+。"
    exit 1
fi
PY_VER=$($PYTHON --version 2>&1)
echo_info "Python: $PY_VER ($PYTHON)"

# -------------------- 2. 检查依赖 --------------------
echo_step "2. 检查 Python 依赖..."
MISSING=""
for pkg in numpy pandas scipy matplotlib seaborn sklearn statsmodels; do
    if ! $PYTHON -c "import $pkg" 2>/dev/null; then
        MISSING="$MISSING  $pkg"
    fi
done
if [ -n "$MISSING" ]; then
    echo_fail "缺少以下依赖包:$MISSING"
    echo "        请运行: pip install -r requirements.txt"
    exit 1
fi
echo_info "所有依赖已就绪。"

# -------------------- 3. 验证模型库导入 --------------------
echo_step "3. 验证模型库模块导入..."
cd "$(dirname "$0")"
for mod in model_library.evaluation model_library.prediction model_library.optimization model_library.statistics model_library.differential utils.data_loader utils.visual; do
    if $PYTHON -c "import $mod" 2>/dev/null; then
        echo "        [OK] $mod"
    else
        echo_fail "✗ $mod 导入失败"
        exit 1
    fi
done
echo_info "所有模块导入成功。"

# -------------------- 4. 虚拟赛题全流程演示 --------------------
echo_step "4. 运行虚拟赛题全流程演示..."
DEMO_DIR="results/demo_$(date +%Y%m%d_%H%M%S)"
export DEMO_DIR
mkdir -p "$DEMO_DIR"

$PYTHON << 'PYEOF'
import os, sys, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 设置中文字体
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
print("【问题1】基于 AQI、PM2.5、PM10、SO2、NO2、CO、O3 六个指标，")
print("         对 12 个城市的空气质量进行综合评价并排名。")
print("【问题2】基于过去 36 个月的 AQI 历史数据，预测未来 3 个月的趋势。")
print()

# ---- 问题1：综合评价 ----
print(">> 问题 1 / 步骤 1：构造虚拟数据 ...")
np.random.seed(42)
n_cities, n_indicators = 12, 6
cities = [f"城市{i+1}" for i in range(n_cities)]
indicators = ["AQI", "PM2.5", "PM10", "SO2", "NO2", "CO"]

# 模拟各城市指标（部分好、部分差）
base = np.random.uniform(30, 120, (n_cities, n_indicators))
# 让城市1-3空气质量较优，城市10-12较差
base[:3]  *= 0.5
base[9:]  *= 1.8
data_df = pd.DataFrame(base, index=cities, columns=indicators)
data_df.to_csv(f"{out_dir}/mock_city_air_quality.csv", encoding="utf-8-sig")
print(f"    已生成 {n_cities} 个城市 × {n_indicators} 个指标 → {out_dir}/mock_city_air_quality.csv")

print(">> 问题 1 / 步骤 2：调用 evaluation 模块（熵权法 + TOPSIS）...")
from model_library.evaluation import entropy_weight, topsis

weights = entropy_weight(base)
scores = topsis(base, weights, impacts=np.array([-1]*n_indicators))
rank = np.argsort(-scores) + 1  # 得分越高排名越前

result_df = pd.DataFrame({
    "城市": cities,
    "TOPSIS得分": np.round(scores, 4),
    "排名": rank.astype(int)
}).sort_values("排名")
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
print(f"    图表已保存 → {out_dir}/problem1_bar.png")

# ---- 问题2：预测 ----
print()
print(">> 问题 2 / 步骤 1：生成 36 个月虚拟 AQI 数据 ...")
np.random.seed(123)
t = np.arange(1, 37)
trend = 80 + 0.2 * t
seasonal = 15 * np.sin(2 * np.pi * t / 12)
noise = np.random.normal(0, 5, 36)
aqi_series = trend + seasonal + noise
aqi_series = np.maximum(aqi_series, 10)
pd.DataFrame({"月份": t.astype(int), "AQI": np.round(aqi_series, 2)}).to_csv(
    f"{out_dir}/mock_aqi_timeseries.csv", encoding="utf-8-sig", index=False
)
print(f"    已生成 36 个月数据 → {out_dir}/mock_aqi_timeseries.csv")

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
print(f"    图表已保存 → {out_dir}/problem2_forecast.png")

# ---- 汇总报告 ----
print()
print("=" * 60)
print("  [OK] 全流程验证完成！")
print("=" * 60)
print(f"  所有输出文件位于: {out_dir}/")
for f in sorted(os.listdir(out_dir)):
    print(f"    - {f}")
print()
print("  工具链状态：正常 [PASS]")
print("  模型库导入：正常 [PASS]")
print("  数据生成：正常 [PASS]")
print("  综合评价：正常 [PASS]")
print("  预测建模：正常 [PASS]")
print("  图表输出：正常 [PASS]")
PYEOF

# -------------------- 5. 检查输出文件 --------------------
echo_step "5. 检查 Demo 输出文件..."

REQUIRED_FILES=(
    "$DEMO_DIR/mock_aqi_timeseries.csv"
    "$DEMO_DIR/mock_city_air_quality.csv"
    "$DEMO_DIR/problem1_bar.png"
    "$DEMO_DIR/problem1_ranking.csv"
    "$DEMO_DIR/problem2_forecast.png"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -s "$file" ]; then
        echo_fail "输出文件缺失或为空: $file"
        exit 1
    fi
    echo "        [OK] $file"
done

echo_info "Demo 输出文件检查通过。"

echo ""
echo_info "工具链完整性验证通过！"
echo "        查看结果: ls $DEMO_DIR/"
