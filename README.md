# CUMCM-AI-Assistant v1.5.0

数学建模竞赛 AI 全流程智能体 — 从审题到论文，一条龙辅助。

> 面向 Claude Code 的数学建模 Skill，内置三角色流水线（建模手→编程手→论文手）、教练核验点、
> 5 质量门（含 W2 自动审计）、数据预处理检查清单、AI 使用台账、稳健性分析、
> 方法选择决策树、可运行模型库（~3700 行 Python）、出版级可视化、LaTeX/Word 双管线。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 验证环境
python check_env.py --features data,visualization,optimization,statistics

# 3. 启动 Claude Code
claude

# 4. 对 AI 说："开始按 CLAUDE.md 流程处理这道赛题"
# AI 将自动按照 建模手→编程手→论文手 的流水线推进，每阶段派发质量门核验
```

## 核心流程

数学建模竞赛被拆为 **三角色流水线**，按阶段执行，每阶段有独立交付物和只读 Subagent 质量门：

| 阶段 | 角色 | 交付物 | 质量门 |
|------|------|--------|--------|
| 1 | 建模手 | 题目分析报告、术语表格 | M1 — 模型-证据核验 |
| 2 | 编程手 | 可运行代码、结果表格、≥9 张出版级图表、复现清单 | P1→P2 — 可复现性核验 |
| 3 | 论文手 | 完整论文（Word/LaTeX+PDF） | W1→W2 — 证据链+全文一致性 |

**5 质量门协议**：每阶段结束派发独立只读 Subagent 核验，返回 PASS/FAIL/BLOCKED 证据回执。详见 `references/Subagent调度.md`。

## 项目结构

```
├── CLAUDE.md                     ← 系统指令（8条强制约束 + 三角色路由 + 渐进加载）
├── README.md                     ← 本文件
├── CHANGELOG.md                  ← 完整版本记录（v1.0.0 → v1.2.0）
├── requirements.txt              ← Python 依赖
├── check_env.py                  ← 环境检查（按 feature 动态验证）
├── run_demo.sh / run_demo.bat    ← 工具链一键验证脚本
│
├── model_library/                ← ★ 可运行模型代码库（~3700 行）
│   ├── evaluation.py             ← 熵权法 / TOPSIS / 模糊综合评价 / AHP
│   ├── prediction.py             ← GM(1,1) / ARIMA / LSTM / 指数平滑 + 过拟合检测
│   ├── optimization.py           ← 线性/整数规划 / 遗传算法 / 模拟退火 / MINLP
│   ├── statistics.py             ← 多元回归(VIF) / Ridge/Lasso / PCA / 聚类 + 过拟合
│   └── differential.py           ← ODE 数值解 / 一维热方程 FTCS
│
├── utils/                        ← 工具模块
│   ├── data_loader.py            ← 多格式数据读取（CSV/Excel/MATLAB/JSON/TXT）
│   └── visual.py v1.1.0          ← 出版级图表（色盲调色板、PNG+SVG 双格式）
│
├── prompts/                      ← 流程控制
│   ├── _README.md                ← 旧版阶段提示词（保留兼容）
│   └── roles/                    ← ★ 三角色工作流（v1.1.0 新增）
│       ├── 建模手/               ← SKILL.md + 工作流程 + 常见模式 + 质检清单
│       ├── 编程手/               ← SKILL.md + 可视化规范 + 图表选择与避坑
│       │   └── references/       ←   常见模式 + 质检清单
│       └── 论文手/               ← SKILL.md + 章节模板 + 写作规范 + 英文化工作流
│
├── references/                   ← 参考资料
│   ├── 论文规范摘要.md            ← 校赛+国赛格式规范
│   ├── Subagent调度.md           ← ★ 质量门协议（派发/回执/反馈回路）
│   ├── 数据预处理检查清单.md      ← ★ 五大类通用检查项（v1.3.0）
│   ├── AI使用台账模板.md          ← ★ 三阶段 AI 使用记录（v1.3.1）
│   └── roles/
│       ├── 编程手/scripts/        ← ★ 辅助脚本
│       │   ├── figure_audit.py   ← 图表审计（DPI/JPEG禁用/SVG配对）
│       │   ├── plot_style.py     ← 出版级样式独立脚本
│       │   └── repro_manifest.py ← 复现清单生成（seed/SHA-256/依赖快照）
│       └── 论文手/scripts/        ← ★ W2 自动审计（v1.4.0）
│           └── paper_audit.py    ← 论文自动审计（图表引用/章节结构/数值交叉/编译/提交清单）
│
├── assets/                       ← ★ 算法资产库（v1.1.0+）
│   ├── README.md                 ← 7类60+种算法索引 + 速查表
│   ├── 方法选择决策树.md          ← ★ 三层方法选择体系：Domain→Subdomain→Method（v1.4.0）
│   ├── 04-图论与网络分析算法说明.md
│   ├── 06-综合类算法说明.md      ← 蒙特卡洛/排队论/博弈论/元胞自动机/马尔可夫
│   └── 07-机器学习算法说明.md    ← 随机森林/AdaBoost/Isolation Forest + 使用原则
│
├── tools/                        ← ★ 独立工具链（v1.2.0 新增）
│   ├── latex/                    ← LaTeX 论文管线
│   │   └── scripts/latex_paper.py  ← doctor/init/build/validate
│   ├── docx/                     ← Word 论文管线
│   │   └── scripts/              ← paper_format（三线表）+ equations（LaTeX→OMML）
│   └── paper_search/             ← 双引擎文献检索（OpenAlex + Crossref）
│
├── template/                     ← 论文模板
│   ├── paper.tex                 ← LaTeX 模板（CUMCM 格式）
│   ├── paper.docx                ← Word 备用模板
│   └── README_compile.md         ← LaTeX 编译指南
│
├── examples/                     ← 范文分析
│   └── 分析总结.md               ← 两篇高分论文结构/模型/图表/写作技巧
│
└── code/ figures/ data/ results/ ← 工作输出目录
```

## 模型速查

| 问题场景 | 首选模型 | 代码位置 |
|----------|---------|---------|
| 综合评价 | 熵权法 + TOPSIS / AHP / 模糊评价 | `model_library/evaluation.py` |
| 预测问题 | GM(1,1) / ARIMA / LSTM（大数据） | `model_library/prediction.py` |
| 优化问题 | 线性规划 / 整数规划 / 遗传算法 | `model_library/optimization.py` |
| 微分方程 | ODE 数值解 / PDE 有限差分 | `model_library/differential.py` |
| 统计分析 | 多元回归 / PCA / K-means / 层次聚类 | `model_library/statistics.py` |
| 图论与网络 | 最短路径 / 网络流 / 关键路径 | `assets/04-*.md` |
| 综合类 | 蒙特卡洛 / 排队论 / 博弈论 / 元胞自动机 | `assets/06-*.md` |
| 机器学习 | 随机森林 / AdaBoost / Isolation Forest | `assets/07-*.md` |

## 工具链速查

| 工具 | 命令 | 功能 |
|------|------|------|
| 环境检查 | `python check_env.py --features data,optimization` | 按需验证依赖 |
| 图表审计 | `python references/roles/编程手/scripts/figure_audit.py figures/` | 检查 DPI/格式/数量 |
| 论文审计 | `python references/roles/论文手/scripts/paper_audit.py template/paper.tex --compile` | 图表引用/章节/数值交叉/编译 |
| 复现清单 | `python references/roles/编程手/scripts/repro_manifest.py --seed 42 --inputs data/` | 生成 SHA-256 快照 |
| LaTeX 管线 | `python tools/latex/scripts/latex_paper.py doctor` | 检查/初始化/编译/校验 |
| Word 管线 | `python tools/docx/scripts/paper_format.py validate --docx paper.docx` | 格式化+校验 |
| 公式转换 | `python tools/docx/scripts/equations.py convert "E=mc^2"` | LaTeX→Unicode |
| 文献检索 | `python tools/paper_search/scripts/hybrid_scholar.py "GM(1,1) prediction"` | 双引擎检索 |

## 可视化标准

- 色盲友好调色板（Wang / Tol Bright / Tol Muted / IBM），禁用彩虹色阶
- 出版级样式（白底、无网格、无上/右脊线、7.5pt 字体）
- PNG（≥300 DPI）+ SVG 双格式导出，灰阶预览自检
- 三类图体系：`raw_`（原始数据）/ `process_`（处理过程）/ `result_`（最终结果），每类 ≥3 张
- 详见 `prompts/roles/编程手/references/可视化规范.md`

## 论文格式要点

- **格式优先级**：模板冲突时先确认参赛竞赛类型（校赛/华数杯/国赛/美赛），按当前竞赛官方模板执行
- **编译方式**：XeLaTeX（推荐 `latexmk -xelatex`）
- **字体要求**：正文宋体小四号，一级标题黑体四号居中，行距 1.25 倍
- **页边距**：上下左右 2.5 cm；**无页眉**
- **摘要**：≤ 1 页，含关键词
- **正文**：≤ 30 页（不含附录）；附录含完整可运行源代码
- **英文论文（MCM/ICM）**：参考 `prompts/roles/论文手/references/英文化工作流.md`
- 详细规范见 `references/论文规范摘要.md`

## 防过拟合规则

- 确定模型前须对比本题与范文场景差异
- 雷同模型须列至少 1 条差异化改进点
- 论文必须包含替代模型对比
- 拟合模型须输出训练/测试误差对比

## 资源获取指南

因版权原因，以下资源未上传至仓库，需自行获取：

| 资源 | 获取方式 |
|------|----------|
| CUMCM 格式规范 PDF | [mcm.edu.cn](http://www.mcm.edu.cn) → 通知公告 |
| 优秀论文全文 | 知网搜索"数学建模"或 [CUMCM 优秀论文](http://www.mcm.edu.cn) |
| 校赛规范 | 向校内数学建模协会索取 |

> 仓库已提供 `references/论文规范摘要.md` 和 `examples/分析总结.md` 作为快速参考。

## 注意事项

- 需自行配置 Claude Code 连接后端 API
- **严禁直接套用范文模型搭配** — 须基于本题数据特征和问题结构重新判断
- 遵守竞赛规则：使用 AI 工具须在论文附录中提交 AI 工具使用说明
- 所有结果须经数据验证，`.gitignore` 已保护版权文件和临时产物

## 版本历史

| 版本 | 日期 | 主要变化 |
|------|------|---------|
| v1.0.0 | 2026-05-29 | 初始发布：模型库 + 论文模板 + 10 阶段提示词 + demo |
| v1.1.0 | 2026-08-03 | 三角色流水线 + 5 质量门 + 出版级可视化 + 算法资产库 + 复现机制 |
| v1.2.0 | 2026-08-03 | LaTeX/Word 论文管线 + 双引擎文献检索 + 英文写作工作流 |
| v1.3.0 | 2026-08-05 | 数据预处理检查清单 + 建模规范软化（去铁律化）+ 数据探索必做步骤 |
| v1.3.1 | 2026-08-05 | AI 使用台账（三阶段记录）+ 稳健性分析（敏感性扫描融入 P2） |
| v1.3.2 | 2026-08-05 | 教练角色重设计：从"金牌教练指导"转为轻量"教练核验点"自检 |
| v1.4.0 | 2026-08-07 | W2 自动审计层（paper_audit）+ 方法选择决策树（三层体系+双向索引） |
| v1.5.0 | 2026-08-09 | 竞争机制（候选池→P1淘汰）+ 回退机制（两级）+ 模板冲突规则（约束#7） |

详见 [CHANGELOG.md](CHANGELOG.md)。
