---
name: 论文手
description: 数学建模第三阶段——把结果写成符合官方格式的论文。
---

# 论文手

## 开始门
- 必须拿到 P2 通过回执和全部结果文件，才能开始论文撰写。
- **第一步：确认参赛竞赛类型**（校赛/华数杯/国赛/美赛），记录于论文元信息中。后续所有模板选择、格式规范、页数上限等决策均以此为据。不同模板冲突时，以当前竞赛官方模板为准，不得擅自决定优先级。

## 固定交付物
- `template/paper.tex`（或 `template/paper.docx`）— 填充完成的论文
- 编译后的 PDF（若用 LaTeX）

## 官方规则优先级
- mcm.edu.cn（CUMCM）与 COMAP（MCM/ICM）官方要求最高
- CUMCM 硬约束：摘要 ≤1 页；正文 ≤30 页（无官方最低页数要求）
- 校赛规范与国赛规范冲突时，优先遵循校赛规范

## 执行顺序
1. **锁定官方规则与格式**：首先确认当前参加的竞赛类型（校赛/华数杯/国赛/美赛），然后加载该竞赛对应的官方模板和格式规范。查阅 `references/论文规范摘要.md`。
2. **检查输入**：确认 P2 回执、结果文件、图表、复现清单、**P1 竞争对比表**齐全
3. **Claim-Evidence 映射**：列出论文中每个结论及其对应的证据来源（数据/公式编号/图表编号/文献）
4. **W1 质量门**：派发只读 Subagent 核验证据大纲，大纲通过后才写长正文
5. **撰写正文**（按章节模板结构）：
   - 摘要（最后写）
   - 问题重述
   - 问题分析
   - 模型假设与符号说明
   - 模型建立与求解（核心章节）
   - 结果分析
   - 模型评价与推广
   - 参考文献
   - 附录（含完整代码）
6. **格式校验**：
   - 先运行 `python references/roles/论文手/scripts/paper_audit.py template/paper.tex --figures-dir figures/ --results-dir results/ --compile --project-root .` 秒级拦截硬错误
   - 再对照 `references/论文规范摘要.md` 逐项人工检查
7. **W2 质量门**：paper_audit 通过后，派发只读 Subagent 核验全文一致性（公式/术语/文献/逻辑自洽）
8. 按 W2 回执返工，直至 PASS。
9. **确认 AI 使用台账**：检查 `references/AI使用台账模板.md` 三阶段均已填写，汇入论文的 AI 使用声明。

## 教练核验点

在以下节点暂停，切换旁观视角自检：

1. **Claim-Evidence 映射后**：每个结论都有可追溯的证据来源吗？有无无依据的断言？
2. **交付前**：paper_audit 通过了吗？公式/图表/文献/格式一致吗？AI 使用台账完整吗？

## 写作原则
- 每个结论必须有可追溯证据
- 术语和符号必须与"术语表格.md"一致
- 不做无来源的断言，不编造数据和文献
- 图表引用格式：`图\ref{fig:qN_xxx}`、`表\ref{tab:qN_xxx}`
- 模型评价部分必须包含替代模型对比（引用 P1 竞争对比表中的实际指标，不做定性空谈）

## 何时加载
| 场景 | 加载内容 |
|------|---------|
| 开局 | 本文档 + `references/roles/论文手/references/工作流程.md` |
| 写正文前 | `references/roles/论文手/references/章节模板.md` |
| 写作中 | `references/roles/论文手/references/写作规范.md` |
| 格式检查 | `references/论文规范摘要.md` + `references/roles/论文手/references/论文格式规范.md` |
| 自动审计 | `python references/roles/论文手/scripts/paper_audit.py --help` |
| 用 LaTeX | `references/roles/论文手/references/LaTeX格式规范.md` |
| 自检 | `references/roles/论文手/references/质检清单.md` |
