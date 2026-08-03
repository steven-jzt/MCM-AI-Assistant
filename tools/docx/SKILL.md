---
name: docx-tools
description: Word 论文格式化工具 — 三线表生成、页边距设置、字体段落格式。
---

# Word 论文工具

## 命令

| 工具 | 功能 |
|------|------|
| `paper_format.py` | Word 论文格式化（页边距、字体、三线表、标题） |
| `equations.py` | LaTeX → OMML 公式转换（Word 原生数学公式） |

## 使用方式

```python
from tools.docx.scripts.paper_format import (
    new_document, setup_page, heading1, heading2, body,
    three_line_table, equation, save_document, validate_paper_structure
)

# 创建新文档
doc = new_document()
setup_page(doc, contest="cumcm")

# 添加标题和正文
heading1(doc, "一、问题重述")
body(doc, "这是正文内容……")

# 插入三线表
three_line_table(doc, headers=["指标", "值", "单位"], rows=[["GDP", "120.5", "亿元"]])

# 校验并保存
issues = validate_paper_structure(doc, contest="cumcm")
save_document(doc, "完整论文.docx")
```

## 依赖
- python-docx（Word 文档操作）
- 无需安装 Word 或 LibreOffice
