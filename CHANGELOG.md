# Changelog

本文件记录项目的所有重要变更。版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [v1.0.0] — 2026-05-29

### 新增
- 初始发布，完整的数学建模竞赛 AI 辅助工具链
- `CLAUDE.md` 系统指令：金牌教练角色设定、五步工作流程、防思维过拟合规则
- `model_library/` 模型代码库（5 个模块）
  - `evaluation.py`：熵权法、TOPSIS、模糊综合评价、AHP
  - `prediction.py`：灰色预测 GM(1,1)、ARIMA、指数平滑、LSTM
  - `optimization.py`：线性规划、整数规划、遗传算法、模拟退火
  - `statistics.py`：多元回归、岭回归/Lasso、PCA、K-means、层次聚类
  - `differential.py`：ODE 数值解、一维热传导有限差分
- `utils/` 工具模块
  - `data_loader.py`：多格式数据读取（CSV/Excel/MATLAB/JSON/TXT）
  - `visual.py`：论文级图表绘制（中文字体、300 dpi 输出）
- `template/paper.tex`：LaTeX 论文模板（依据江西财经大学 2026 年规范）
- `template/paper.docx`：Word 备用模板
- `template/README_compile.md`：LaTeX 编译指南
- `references/论文规范摘要.md`：竞赛格式规范摘要（校赛 + 国赛）
- `examples/分析总结.md`：两篇往届优秀论文的结构与技巧分析
- `.gitignore`：版权文件、编译产物、Python 缓存过滤
- `run_demo.sh` / `run_demo.bat`：工具链完整性验证脚本
