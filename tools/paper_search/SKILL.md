---
name: paper-search
description: 双引擎学术文献检索 — OpenAlex + Crossref 交叉验证、去重与相关性排序。
---

# 文献检索工具

## 双引擎策略

| 引擎 | 特点 | 需要 API Key |
|------|------|-------------|
| OpenAlex | 免费、覆盖面广（2.5 亿+ 文献）、结构化元数据 | 否 |
| Crossref | 免费、DOI 权威来源、引用网络 | 否 |

两引擎结果交叉验证：DOI 完全匹配 → 确认；标题模糊匹配（≥0.85 相似度）→ 合并。

## 使用方式

```bash
# 基本检索
python tools/paper_search/scripts/hybrid_scholar.py "grey prediction model GM(1,1) application"

# 指定结果数量
python tools/paper_search/scripts/hybrid_scholar.py "entropy weight TOPSIS" --limit 10

# 输出 JSON
python tools/paper_search/scripts/hybrid_scholar.py "NSGA-II multi-objective optimization" --json
```

## 输出格式

每篇文献包含：
- 标题、作者、年份、DOI
- 来源引擎标记（openalex/crossref/cross_validated）
- 摘要（如有）
- 引用次数（如有）
- APA 格式引用字符串
