---
name: latex-paper
description: LaTeX 论文工程管理工具 — doctor/init/build/validate。
---

# LaTeX 论文管线

## 命令

| 命令 | 功能 |
|------|------|
| `doctor` | 检查 LaTeX 工具链（xelatex/latexmk）是否可用 |
| `init` | 从 `template/paper.tex` 初始化论文工程 |
| `build` | 编译 LaTeX 工程生成 PDF |
| `validate` | 校验编译产物（页数、引用、公式数量） |

## 使用方式

```bash
# 检查工具链
python tools/latex/scripts/latex_paper.py doctor

# 初始化论文工程（将模板复制到 PROJECT_ROOT）
python tools/latex/scripts/latex_paper.py init --output ./paper_project

# 编译
python tools/latex/scripts/latex_paper.py build --project ./paper_project

# 校验
python tools/latex/scripts/latex_paper.py validate --project ./paper_project --pdf ./paper_project/main.pdf
```

## 编译引擎优先级
1. `latexmk -xelatex`（首选，自动处理交叉引用和参考文献）
2. `xelatex` + `bibtex` + 两次 `xelatex`（回退方案）

## 校验项
- 无未定义引用（`LaTeX Warning: Reference ... undefined`）
- 无缺失图片
- 页码在官方限制内
- 公式/图表/表格数量达标
