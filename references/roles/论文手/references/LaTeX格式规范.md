# LaTeX 论文格式规范

> 论文结构、文档类、页面、字体、页数必须遵循目标竞赛当届官方规则与官方模板。本文件给出 LaTeX 生成流程与校验要点；编译环境、字体配置与常见问题见 `template/README_compile.md`。

## 唯一权威来源

- CUMCM：`http://www.mcm.edu.cn/`
- MCM/ICM：`https://www.comap.com/contests/mcm-icm`

## 模板驱动生成

1. 从 `template/paper.tex`（CUMCM 格式）初始化论文工程，保留模板导言区与页面结构。
2. 用 `tools/latex/scripts/latex_paper.py` 管理工程（完整入口见 `tools/latex/SKILL.md`）：

```bash
python tools/latex/scripts/latex_paper.py doctor                                   # 检查工具链（xelatex/latexmk）
python tools/latex/scripts/latex_paper.py init --output ./paper_project            # 初始化工程
python tools/latex/scripts/latex_paper.py build --project ./paper_project          # 编译
python tools/latex/scripts/latex_paper.py validate --project ./paper_project \
    --pdf ./paper_project/main.pdf                                                # 校验
```

3. 只编辑正文与明确占位位置，不破坏模板结构。
4. 把编程手真实图表和核验后的参考文献放入工程，使用项目内相对路径。

## 公式、图表与引用

- 公式保留为原生 LaTeX，并在实际编译 PDF 中检查换行、编号与字体。
- 每图每表都有题注、真实内容与 `\label{}`，正文至少用 `\ref{}` 引用一次。
- 正文 `\cite{}` 键必须能在 `.bib` 或 `bibitem` 中找到。

## 编译与校验

- 编译引擎：XeLaTeX（首选 `latexmk -xelatex`，回退 `xelatex` + `bibtex` + 两次 `xelatex`）。
- 校验项：无未定义引用、无缺失图片、页码在官方限制内、公式/图表/表格数量达标。
- 详细编译命令、字体配置与常见问题见 `template/README_compile.md`。

## 交付

交付完整源码工程 + 由该工程实际编译得到的 PDF；不要只交一个脱离 `.cls/.sty/.bib` 依赖的单个 `.tex` 文件。
