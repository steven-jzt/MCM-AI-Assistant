# LaTeX 论文模板编译说明

## 环境要求

| 组件 | 推荐版本 | 说明 |
|---|---|---|
| TeX 发行版 | TeX Live 2024+ / MiKTeX 24+ | 需包含 `xelatex` 和 `ctex` 宏包 |
| 中文字体 | SimHei + Songti SC / SimSun | Windows 自带；macOS 用 Songti SC |
| 编辑器 | VS Code + LaTeX Workshop / TeXstudio | 任选其一 |

## 依赖宏包

以下宏包在完整 TeX Live / MiKTeX 安装中默认包含：

`ctex` `geometry` `setspace` `graphicx` `amsmath` `amssymb`
`booktabs` `longtable` `hyperref` `caption` `subcaption`
`enumitem` `fancyhdr` `float` `cite` `listings` `xcolor`

若提示缺失，使用包管理器安装：

```bash
# TeX Live
tlmgr install <包名>

# MiKTeX（自动安装缺失包）
```

## 编译命令

```bash
# 在 template/ 目录下执行：

# 单次编译（快速预览）
xelatex paper.tex

# 完整编译（含交叉引用和目录，推荐）
xelatex paper.tex
xelatex paper.tex
```

> **注意**：必须使用 **XeLaTeX** 而非 pdfLaTeX，因为模板依赖 `fontspec` 加载系统字体。

## 字体配置

模板默认字体设置：

```latex
\setCJKmainfont{Songti SC}   % 正文宋体 → macOS
\setCJKsansfont{SimHei}      % 标题黑体 → Windows
```

### 字体适配

- **Windows**：SimHei 和 SimSun 通常已安装，无需修改
- **macOS**：将 `\setCJKmainfont` 改为 `Songti SC` 或 `STSongti-SC`
- **Linux**：安装中文字体包后指定名称，如 `Noto Serif CJK SC`

若编译报"font not found"，查询系统可用中文字体：

```bash
# macOS / Linux
fc-list :lang=zh | grep -i "song\|hei\|宋\|黑"

# 或在模板中改用 ctex 默认字体（无需指定系统字体名）：
\documentclass[12pt, a4paper, fontset=windows]{ctexart}  % Windows
\documentclass[12pt, a4paper, fontset=mac]{ctexart}      % macOS
```

## 输出文件

```
template/
  ├── paper.tex          # 源文件
  ├── paper.pdf          # 编译输出（提交用）
  ├── paper.aux          # 交叉引用辅助文件
  └── paper.log          # 编译日志（调试用）
```

## VS Code 配置

安装 LaTeX Workshop 插件后，在 `settings.json` 中添加：

```json
{
  "latex-workshop.latex.recipes": [
    {
      "name": "xelatex × 2",
      "tools": ["xelatex", "xelatex"]
    }
  ],
  "latex-workshop.latex.tools": [
    {
      "name": "xelatex",
      "command": "xelatex",
      "args": [
        "-synctex=1",
        "-interaction=nonstopmode",
        "-file-line-error",
        "%DOC%"
      ]
    }
  ]
}
```

## 常见问题

| 症状 | 原因 | 解决办法 |
|---|---|---|
| `! LaTeX Error: File 'ctexart.cls' not found` | 未安装 ctex 宏包 | `tlmgr install ctex` |
| 中文显示为空白/方块 | 系统缺少对应字体 | 改用 fontset 选项或安装字体 |
| 图片不显示 | 图片路径不正确 | 确认 `figures/xxx.png` 存在 |
| 参考文献引用显示 [?] | 未二次编译 | 再执行一次 `xelatex` |
| `! Dimension too large` | 图片尺寸过大 | 调整 `\includegraphics[width=...]` |
