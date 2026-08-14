# Changelog

本文件记录项目的所有重要变更。版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [v1.6.0] — 2026-08-14

### 新增 — 原生化适配当前 Claude Code

- **根 `SKILL.md`**：项目入口从 `CLAUDE.md`（项目记忆）迁移为 Claude Code 原生 Skill（`name: mcm-ai-assistant` + 描述 frontmatter），编排逻辑重组为 10 条强制约束 + 三角色路由 + 渐进加载 + 质量门 + 竞争/回退机制 + 模型速查。
- **原生质量门 Subagent**：新增 `.claude/agents/{m1,p1,p2,w1,w2}-gate.md`，把 M1/P1/P2/W1/W2 五个质量门固化为只读 Subagent 定义，主 Agent 可按名（`subagent_type`）派发。
- **SKILL_ROOT / PROJECT_ROOT 契约**：明确只读技能资产（`model_library/`、`utils/`、`tools/`、`references/`、`assets/`、`template/`）与赛题工作目录（`code/`、`data/`、`figures/`、`results/`）分离，支持安装为技能后在任意项目复用。
- **`VERSION` 文件**：新增版本号 `1.6.0`。

### 改进 — 目录重构

- 角色文档 `prompts/roles/` 迁入 `references/roles/`，与既有 `references/roles/*/scripts/` 统一，修复角色 SKILL.md 中的相对路径断链。
- 旧版扁平提示词（`prompts/*.md`）移入 `prompts/legacy/` 标记废弃。
- `CLAUDE.md` 降级为薄指针（指向 `SKILL.md` + 安装说明），保留给把仓库当工作项目使用的用户。
- `README.md` 增加「安装为技能」方式，说明与第三方 `math-modeling` 技能并存。

---

## [v1.5.0] — 2026-08-09

### 新增 — 竞争机制与回退机制
- **竞争机制**：建模手建立候选模型池（每个子问题 2-3 个候选）→ P1 阶段在同一 mini-batch 上定量竞争淘汰
  - 淘汰规则：复杂模型全指标不如简单基准则淘汰；指标接近（<10%）全部保留；物理意义错误立即淘汰
  - 产出竞争对比表（核心指标 + 运行时间 + 数据假设满足度）
  - 若所有候选不满足要求 → 触发二阶回退，通知建模手重建候选池
- **回退机制**：两级回退体系
  - 一阶回退：同阶段内修复，按质量门回执指引返工
  - 二阶回退：退回上一阶段重新选择方案（触发条件：P1 所有候选淘汰/W1 证据链断裂/W2 全文一致性崩溃）
  - 约束 #1 增加例外：回退机制允许阶段流转，不视为违反顺序执行规则
- **模板冲突规则**（约束 #7）：模板冲突时根据当前参赛竞赛类型决定优先级，禁止擅自选定

### 改进
- P1 质量门升级：从"跑通一个 MVP"升级为"候选模型竞争淘汰"
- 建模手步骤 5 从"选择模型"改为"建立候选模型池"，不做纸面最终推荐
- 论文手开始门增加"第一步：确认参赛竞赛类型"
- 论文手模型对比写作要求引用 P1 竞争数据
- 5 处"校赛优先"硬编码替换为参赛竞赛类型判定规则
- CLAUDE.md 版本号升级至 v1.5.0

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
- `references/roles/编程手/references/可视化规范.md`：三类图体系、出版级样式基准、图表合同（14字段）、导出自检循环
- `references/roles/编程手/references/图表选择与避坑.md`：图表选择四问、数学建模场景速查表、15 条避坑清单

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

## [v1.4.0] — 2026-08-07

### 新增 — W2 自动审计层 + 方法选择决策树
- **`references/roles/论文手/scripts/paper_audit.py`**：论文自动审计脚本（标准库），W2 第一层秒级拦截硬错误
  - 图表引用完整性检查（figures/ 图片 ↔ 论文引用）
  - 表格引用完整性检查（\label{tab:} ↔ \ref{tab:}）
  - 章节结构检查（必要章节/摘要/关键词/页数估算）
  - 数值交叉校验（论文数值 ↔ results/ CSV 计算结果）
  - LaTeX 编译检查（xelatex/pdflatex 自动检测与编译验证）
  - DOCX 基础结构检查（段落/图片/表格/页数）
  - 提交清单生成（代码/图表/复现清单/台账就绪状态）
- **`assets/方法选择决策树.md`**：三层方法选择体系（Domain → Subdomain → Method）
  - 7 大领域、20+ 子领域、50+ 方法，含适用条件、数据要求、代码位置
  - 反向索引：从数据特征出发收敛到方法（时间序列/横截面/网络/机理/不确定性五种数据形态）
  - 经典方法组合表（已验证有效的 9 种搭配）
  - "从简单到复杂"对照表

### 改进
- W2 质量门升级为**两层校验**：自动脚本（秒级硬错误）→ Subagent 深度审查（语义一致性）
- 论文手 SKILL.md 格式校验步骤增加 paper_audit 自动审计
- Subagent调度.md W2 反馈回路更新为"先跑 paper_audit 再复查"
- 论文手教练核验点交付前增加 paper_audit 通过确认
- assets/README.md 增加方法选择决策树索引

---

## [v1.3.1] — 2026-08-05

### 新增 — AI 使用台账与稳健性分析
- **`references/AI使用台账模板.md`**：三阶段（建模/编程/论文）AI 使用记录模板，满足 CUMCM 2026 AI 披露要求
- CLAUDE.md 强制约束协议新增第 9 条"AI 使用台账"，三阶段结束时填写，W2 核验
- 建模手/编程手/论文手 SKILL.md 各增加台账更新步骤
- W2 质量门新增 AI 使用台账完整性检查

### 改进 — 稳健性分析融入 P2
- P2 质量门关注点从"结果可靠性评估"扩展为"结果可靠性与稳健性分析"，增加关键参数敏感性扫描要求
- CLAUDE.md 工作流步骤 10 扩展为"结果可靠性与稳健性分析"
- Subagent调度.md P2 解除条件与反馈回路同步更新

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
- **`references/roles/论文手/references/英文化工作流.md`** — MCM/ICM 英文写作全流程
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
