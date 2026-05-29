# 常见报错应急处理

> 使用时机：任何阶段遇到报错或卡住时使用。

---

我在 [xxx阶段] 遇到了以下错误，请帮我诊断并修复。

## 错误信息
```
[粘贴完整的报错信息]
```

## 当前上下文
- 正在执行的脚本：[文件路径]
- 使用的数据：[数据文件及其关键字段]
- 最近一次修改：[描述刚才改了什么]
- 预期行为：[应该得到什么结果]

## 要求
1. 分析错误根因（不要只给解决方案）
2. 给出具体修复代码（指出修改哪个文件的哪一行）
3. 说明为什么这个修复是正确的
4. 如果可能有其他潜在问题，一并预警

---

## 常见错误速查

### 1. 中文编码/字体问题
**症状**：`UnicodeEncodeError`、图表中文显示为方块
**常用修复**：
```python
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False
```
**或**：修改 `utils/visual.py` 中的 `_FONT_CANDIDATES` 列表

### 2. 矩阵奇异/不可逆
**症状**：`LinAlgError: Singular matrix`
**常用修复**：
- 检查数据是否存在全零列/行
- 对矩阵加正则化项（ridge）：`np.linalg.inv(X.T @ X + lambda * I)`
- 使用 `np.linalg.pinv` 伪逆替代 `np.linalg.inv`

### 3. 优化不收敛
**症状**：`OptimizeWarning: Maximum number of iterations exceeded`
**常用修复**：
- 增大 `maxiter` 参数
- 换初始点
- 换优化方法（如从 SLSQP 换为 trust-constr）
- 检查目标函数是否光滑

### 4. 灰色预测 GM(1,1) 级比检验不通过
**症状**：`UserWarning: 级比检验未通过`
**常用修复**：
- 对原始序列做平移变换（所有值加一个常数），使新序列通过检验
- 换用指数平滑法或 ARIMA 作为备选方案

### 5. 数据读取失败
**症状**：`FileNotFoundError`、`UnicodeDecodeError`
**常用修复**：
- 确认文件路径，使用 `utils/data_loader.py` 的统一接口
- CSV 尝试不同编码：`encoding="gbk"` / `encoding="utf-8-sig"`
- Excel 文件指定 sheet_name

### 6. 内存不足
**症状**：`MemoryError`
**常用修复**：
- 使用 `pd.read_csv(chunksize=10000)` 分块读取
- 将 float64 转为 float32
- 删除中间变量 `del df_temp`

### 7. LaTeX 编译失败
**症状**：`! LaTeX Error`、中文不显示
**常用修复**：
- 确认使用 `xelatex`（非 `pdflatex`）
- 检查系统是否安装了中文字体（SimHei, Songti SC）
- 参考 `template/README_compile.md` 排查

---

请直接粘贴报错信息开始诊断。
