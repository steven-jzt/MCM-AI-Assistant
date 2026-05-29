# CUMCM-AI-Assistant

数学建模竞赛 AI 辅助系统，基于 Claude Code + DeepSeek，用于快速拆题、建模、编码、绘图和论文撰写。适用于全国大学生数学建模竞赛（CUMCM）及校级选拔赛。

## 快速开始

1. **安装 Python 依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **启动 Claude Code**：在项目根目录运行：
   ```bash
   claude
   ```

3. **放入赛题和数据**，然后说 "开始按 CLAUDE.md 流程处理赛题"，AI 将严格按照竞赛流程完成拆题、建模、编码、绘图与论文片段撰写。

4. **验证工具链**（可选）：运行演示脚本，确认环境无误。
   ```bash
   # macOS / Linux
   bash run_demo.sh

   # Windows
   run_demo.bat
   ```
   脚本将生成虚拟赛题并跑通"综合评价→预测→绘图"全流程，结果输出到 `results/demo_*/`。

## 项目结构

```
├── CLAUDE.md                  # 系统指令：角色设定、输出规范、工作流程、防过拟合规则
├── README.md                  # 本文件
├── requirements.txt           # Python 依赖
│
├── model_library/             # 常用模型代码库（可直接调用或二次修改）
│   ├── evaluation.py          # 综合评价：熵权法 / TOPSIS / 模糊综合评价 / AHP
│   ├── prediction.py          # 预测模型：灰色预测 GM(1,1) / ARIMA / 指数平滑 / LSTM
│   ├── optimization.py        # 优化模型：线性规划 / 整数规划 / 遗传算法 / 模拟退火
│   ├── statistics.py          # 统计分析：多元回归 / 岭回归·Lasso / PCA / K-means / 层次聚类
│   └── differential.py        # 微分方程：ODE 数值解 / 一维热传导有限差分
│
├── utils/                     # 工具模块
│   ├── data_loader.py         # 统一数据读取：CSV / Excel / MATLAB / JSON / TXT
│   └── visual.py              # 论文级图表：自动中文字体、300 dpi 高清输出
│
├── template/                  # 论文模板
│   ├── paper.tex              # LaTeX 模板（依据江西财经大学 2026 年格式规范）
│   ├── paper.docx             # Word 备用模板
│   └── README_compile.md      # LaTeX 编译指南（含 xelatex 配置与 VS Code 设置）
│
├── prompts/                   # 分阶段提示词模板（按比赛阶段选取使用）
│   ├── _README.md             # 使用说明与推荐顺序
│   ├── problem_analysis.md    # 审题与拆解
│   ├── model_selection.md     # 模型推荐与对比
│   ├── modeling_derivation.md # 模型建立与推导
│   ├── code_and_solve.md      # 代码生成、运行与纠错
│   ├── visualization.md       # 图表生成规范
│   ├── paper_writing.md       # 各章节撰写
│   ├── abstract.md            # 摘要专项
│   ├── review_and_check.md    # 终审检查清单
│   └── emergency.md           # 常见报错应急处理
│
├── references/                # 竞赛规范（原始 PDF/DOC 需自行获取，见下方资源指南）
│   └── 论文规范摘要.md         # 格式规范摘要（校赛 + 国赛，含冲突处理优先级）
│
├── examples/                  # 范文分析（原始论文需自行获取，见下方资源指南）
│   └── 分析总结.md             # 两篇优秀论文的模型选择、结构、图表、写作句式分析
│
├── code/                      # 解题过程中生成的代码
├── figures/                   # 生成的图表（高清 PNG/SVG）
├── data/                      # 赛题数据文件
├── results/                   # 求解结果输出
│
├── run_demo.sh                # 工具链验证脚本 (macOS / Linux)
├── run_demo.bat               # 工具链验证脚本 (Windows)
├── CHANGELOG.md               # 版本更新记录
└── .gitignore                 # Git 忽略规则
```

## 工作流程

AI 接收到赛题后，严格按照以下流程处理：

| 步骤 | 内容 | 说明 |
|------|------|------|
| 1. 审题与拆解 | 输出问题结构映射表，保留原题问题编号与层级 | 确保问题依赖关系清晰 |
| 2. 模型推荐 | 每问推荐 2-3 种模型，对比优劣，给出最终推荐 | 含与范文的差异化分析 |
| 3. 模型建立与推导 | 详细假设、符号说明、LaTeX 数学推导 | 假设须附合理性说明 |
| 4. 算法与代码实现 | 可直接运行的 Python 代码 + 可视化 | 代码存入 `code/`，图存入 `figures/` |
| 5. 结果分析与论文撰写 | 结果解释 + 论文片段（问题重述、模型、求解、分析等） | 特别注意摘要质量 |

## 模型速查

| 问题场景 | 优先模型 | 对应模块 |
|----------|----------|----------|
| 综合评价 | 熵权法 + TOPSIS / 模糊综合评价 | `model_library/evaluation.py` |
| 预测问题 | 灰色预测 GM(1,1) / ARIMA / LSTM（大数据量） | `model_library/prediction.py` |
| 优化问题 | 线性规划 / 整数规划 / 遗传算法 | `model_library/optimization.py` |
| 微分方程 | ODE 数值解 / PDE 有限差分 | `model_library/differential.py` |
| 统计分析 | 多元回归 / 主成分分析 / K-means 聚类 | `model_library/statistics.py` |

## 论文格式要点

- **格式优先级**：校赛规范 > 国赛规范（冲突时以校赛为准）
- **编译方式**：XeLaTeX（`xelatex paper`），需 TeX Live / MiKTeX 环境
- **字体要求**：正文宋体小四号，一级标题黑体四号居中，行距 1.25 倍
- **页边距**：上下左右 2.5 cm；**无页眉**
- **摘要**：≤ 1 页，含关键词，中文即可
- **正文**：≤ 30 页（不含附录）；附录含完整可运行源代码
- 详细规范见 `references/论文规范摘要.md`

## 资源获取指南

仓库仅包含自写的代码、模板和分析总结。以下资源因版权原因未上传，需自行获取后放入对应目录：

### 论文模板
| 资源 | 获取方式 | 放入目录 |
|------|----------|----------|
| LaTeX 模板 | 已内置 `template/paper.tex`（可自行修改） | `template/` |
| Word 模板 | 已内置 `template/paper.docx`（可自行修改） | `template/` |
| 更多 LaTeX 模板 | [CTAN](https://ctan.org) 搜索 "cumcm" 或 "latex 数学建模模板" | `template/` |

### 竞赛格式规范
| 资源 | 获取方式 | 放入目录 |
|------|----------|----------|
| CUMCM 论文格式规范 | [全国大学生数学建模竞赛官网](http://www.mcm.edu.cn) → 通知公告 | `references/` |
| 校赛格式规范 | 向校内数学建模协会或教务处索取 | `references/` |

> 仓库已提供 `references/论文规范摘要.md` 作为快速参考，涵盖国赛和校赛的核心要求。

### 优秀论文参考
| 资源 | 获取方式 | 放入目录 |
|------|----------|----------|
| CUMCM 优秀论文 | 知网搜索 "数学建模竞赛" + 题目关键词；或 [CUMCM 官网](http://www.mcm.edu.cn) 优秀论文栏目 | `examples/` |
| 校赛优秀论文 | 向校内数学建模协会或指导老师索取 | `examples/` |

> 仓库已提供 `examples/分析总结.md`，提炼了两篇往届优秀论文的结构、模型、图表和写作技巧，可直接作为风格参考。获取原论文后可对照阅读，获得更深理解。

### .gitignore 已保护
放入上述资源后，`examples/*.pdf`、`references/*.pdf` 等版权文件会被 `.gitignore` 自动忽略，**不会被提交到 GitHub**，可放心本地使用。

## 注意事项

- 需自行配置 Claude Code 连接 DeepSeek（或其他 Anthropic API 兼容后端）
- 范文分析为自行总结，未上传原论文全文，仅做风格参考
- **严禁直接套用范文模型搭配**——每次选题必须基于本题数据特征和问题结构重新判断
- 遵守竞赛规则：若使用 AI 工具，需在论文附录中提交 AI 工具使用说明
- 所有模型结果须经数据验证，拟合模型须输出训练/测试误差对比
