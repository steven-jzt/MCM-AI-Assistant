# Changelog

本文件记录项目的所有重要变更。版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [v1.1.0] — 2026-08-03

### 新增 — 流程工程化升级
- **强制约束协议**（CLAUDE.md）：8 条强制性规则（阶段顺序、文件保护、质量门、Subagent策略、模型数量限制、官方规则优先、可复现性、渐进加载）
- **三角色工作流**：建模手 → 编程手 → 论文手，每角色独立 SKILL.md + 工作流程 + 常见模式 + 质检清单
- **5 质量门机制**（M1/P1/P2/W1/W2）：`references/Subagent调度.md` 定义固定门协议、派发格式、回执格式、反馈回路
- **渐进加载协议**（CLAUDE.md）：每阶段"必读 vs 按需加载"文档表
- **check_env.py**：按 feature 动态验证 Python 依赖（支持 12 种特征）
- **figure_audit.py**：图表审计脚本（DPI、JPEG 禁用、SVG/PNG 配对、分类统计）
- **repro_manifest.py**：复现清单生成器（seed、SHA-256、依赖版本快照、复现命令）
- **plot_style.py**：出版级绘图样式独立脚本（色盲调色板、SCI 风格参数）

### 新增 — 可视化升级
- `utils/visual.py` v1.1.0：色盲友好调色板（Wang/Tol/IBM 四套）、PNG+SVG 双格式导出、出版级样式（`apply_publication_style()`）、灰阶预览、新增 `line_with_ci()` 和 `dual_axis_chart()`
- `prompts/roles/编程手/references/可视化规范.md`：三类图体系、出版级样式基准、图表合同（14字段）、导出自检循环
- `prompts/roles/编程手/references/图表选择与避坑.md`：图表选择四问、数学建模场景速查表、15 条避坑清单

### 新增 — 算法资产库
- `assets/README.md`：算法索引（7类60+种）、十类核心算法、问题类型/数据类型速查表
- `assets/04-图论与网络分析算法说明.md`：最短路径、最小生成树、网络流、关键路径、欧拉/哈密顿、匹配
- `assets/06-综合类算法说明.md`：蒙特卡洛、排队论、博弈论、元胞自动机、马尔可夫链、微分方程
- `assets/07-机器学习算法说明.md`：随机森林、AdaBoost、Isolation Forest + 竞赛使用原则

### 改进
- CLAUDE.md 版本号升级至 v1.1.0
- 工作流程从 5 步扩展为 15 步（含 5 个质量门）
- 模型速查表增加图论/综合/机器学习三类
- 输出规范升级为出版级可视化标准（PNG+SVG、色盲调色板、出版级样式）

---

## [v1.3.0] — 2026-08-05

### 新增 — 数据预处理与建模规范软化
- **`references/数据预处理检查清单.md`**：五大类通用检查项（数据全貌、缺失值、异常值、数据结构性、变量关系），建模手推荐模型前、编程手实现算法前均需完成
- **建模通用提醒**（CLAUDE.md）：4 条软性指导原则（探索数据再建模、从简单到复杂、验证多维度、结果诚实），替代此前的绝对化铁律
- 工作流程阶段一新增"数据探索与预处理"必做步骤（审题拆解之后、模型推荐之前）
- 工作流程阶段二新增"结果可靠性评估"步骤（测量类做不确定度合成，预测类做交叉验证，优化类做灵敏度分析）
- 建模手/编程手 SKILL.md 增加数据优先原则、简单基线对照要求
- 质检清单新增"数据探索与预处理"检查节和"结果可靠性"选检节
- M1/P1/P2 质量门关注点和解除条件更新

### 新增 — 建模模式扩展
- 建模手常见模式新增：模式 12（变量变换+线性回归）、模式 13（变换域分析含数据质量前置）
- 编程手常见模式新增：数据预处理模板、不确定度合成代码模板（测量/反演类）、3 条新陷阱（全量数据被污染、缺误差范围、验证维度单一）

### 改进
- 防思维过拟合规则新增"简单方法对照""结构性断点检查"两条
- 质量门反馈回路补充数据质量分析和结果可靠性评估相关内容
- CLAUDE.md 版本号升级至 v1.3.0

---

## [v1.2.0] — 2026-08-03

### 新增 — 论文管线与文献工具
- **`tools/latex/`** — LaTeX 论文工程管理工具
  - `latex_paper.py`：doctor（工具链检查）/ init（初始化工程）/ build（编译）/ validate（校验页数/公式/图表）
- **`tools/docx/`** — Word 论文格式化工具
  - `paper_format.py`：new_document / setup_page / title / heading1/2 / body / three_line_table（三线表）/ equation / validate_paper_structure
  - `equations.py`：LaTeX→Unicode 数学公式转换器（支持希腊字母、上下标、分数、根号），DOCX 占位符批量替换
- **`tools/paper_search/`** — 双引擎文献检索工具
  - `hybrid_scholar.py`：OpenAlex + Crossref 并行检索，DOI 精确匹配 + 标题模糊去重，相关性过滤，APA 格式引用输出
- **`prompts/roles/论文手/references/英文化工作流.md`** — MCM/ICM 英文写作全流程
  - 英文摘要标准模板（Context→Gap→Approach→Result→Boundary→Implication）
  - 20 条中式英文修正表
  - 动词力度层级（强/中/弱）
  - 学术短语库（引出问题/方法/结果/对比/局限/结论）
  - 段落检查清单 + MCM/ICM 格式差异表
  - 常用中英数学术语对照

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
