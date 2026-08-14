# Prompts 使用说明

本文件夹包含数学建模竞赛各阶段的提示词模板。**使用方法**：将对应阶段的内容直接发送给 Claude Code，AI 将按照 CLAUDE.md 设定的金牌教练角色和流程处理。

## 文件索引与使用时机

| 文件 | 使用时机 | 输入条件 |
|------|----------|----------|
| `problem_analysis.md` | 拿到赛题后，第一步 | 已放入赛题 PDF/Word、数据文件 |
| `model_selection.md` | 问题拆解完成后 | 已完成问题结构映射 |
| `modeling_derivation.md` | 模型选定后 | 已确定每问使用的模型 |
| `code_and_solve.md` | 模型推导完成后 | 已有完整数学公式和算法步骤 |
| `visualization.md` | 代码跑出结果后 | 已有数值结果 |
| `paper_writing.md` | 所有问题求解完成后 | 已有全部结果和图表 |
| `abstract.md` | 正文写完后（最后写） | 论文正文已完成 |
| `review_and_check.md` | 提交前 | 论文、代码、附录已完成 |
| `emergency.md` | 任何遇到报错/卡住的时刻 | 报错信息 |

## 推荐使用顺序

```
审题 → 模型推荐 → 模型推导 → 编码求解 → 可视化 → 论文撰写 → 摘要 → 终审检查
  ↓         ↓          ↓          ↓          ↓          ↓        ↓        ↓
problem   model     modeling   code_and   visuali-   paper_    abstract review
analysis  selection derivation solve      zation     writing
```

## 注意事项

- 每个阶段的提示词假设上一步已完成且有产出，如果跳过步骤请补充上下文
- 可根据实际赛题特点修改提示词中的方括号 `[...]` 占位内容
- `emergency.md` 随时可用，不依赖其他阶段
- 所有提示词均遵循 CLAUDE.md 中的规范（LaTeX 格式、论文规范摘要、防过拟合规则等）
