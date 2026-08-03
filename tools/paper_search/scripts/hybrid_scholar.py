#!/usr/bin/env python3
"""
双引擎学术文献检索 — hybrid_scholar.py
==========================================
OpenAlex + Crossref 双引擎并行检索，DOI 精确匹配 + 标题模糊去重。

使用依赖：
  pip install requests

用法：
  python tools/paper_search/scripts/hybrid_scholar.py "grey prediction GM(1,1)"
  python tools/paper_search/scripts/hybrid_scholar.py "TOPSIS evaluation" --limit 10 --json
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from urllib.parse import quote

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ── 数据模型 ────────────────────────────────────────────────

class HybridPaper:
    """检索结果文献。"""
    __slots__ = ("title", "authors", "year", "doi", "abstract",
                 "citation_count", "source", "cross_validated")

    def __init__(self, title: str, authors: List[str] = None,
                 year: int = None, doi: str = None, abstract: str = "",
                 citation_count: int = 0, source: str = "unknown",
                 cross_validated: bool = False):
        self.title = title
        self.authors = authors or []
        self.year = year
        self.doi = doi
        self.abstract = abstract
        self.citation_count = citation_count
        self.source = source
        self.cross_validated = cross_validated

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "abstract": self.abstract[:300] if self.abstract else "",
            "citation_count": self.citation_count,
            "source": self.source,
            "cross_validated": self.cross_validated,
            "apa": self.apa_citation(),
        }

    def apa_citation(self) -> str:
        """生成 APA 格式引用。"""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."
        year_str = f"({self.year})" if self.year else "(n.d.)"
        return f"{authors_str} {year_str}. {self.title}."


# ── OpenAlex 引擎 ──────────────────────────────────────────

OPENALEX_URL = "https://api.openalex.org/works"


def search_openalex(query: str, limit: int = 10) -> List[HybridPaper]:
    """通过 OpenAlex API 检索文献。"""
    papers = []
    try:
        params = {
            "search": query,
            "per_page": min(limit, 50),
            "sort": "cited_by_count:desc",
        }
        r = requests.get(OPENALEX_URL, params=params, timeout=15,
                         headers={"User-Agent": "MCM-Agent/1.0"})
        r.raise_for_status()
        data = r.json()

        for item in data.get("results", [])[:limit]:
            # 提取作者
            authors = []
            for auth in item.get("authorships", []):
                name = auth.get("author", {}).get("display_name", "")
                if name:
                    authors.append(name)

            # 提取 DOI
            doi = item.get("doi", "")
            if doi:
                doi = doi.replace("https://doi.org/", "")

            # 提取年份
            year = item.get("publication_year")

            # 提取摘要（OpenAlex 使用倒排索引）
            abstract = ""
            ab_idx = item.get("abstract_inverted_index")
            if ab_idx:
                abstract = _reconstruct_abstract(ab_idx)

            papers.append(HybridPaper(
                title=item.get("title", ""),
                authors=authors,
                year=year,
                doi=doi,
                abstract=abstract,
                citation_count=item.get("cited_by_count", 0),
                source="openalex",
            ))
    except Exception as e:
        print(f"[OpenAlex] 检索出错: {e}", file=sys.stderr)

    return papers


def _reconstruct_abstract(inverted_index: dict) -> str:
    """从 OpenAlex 倒排索引重建摘要文本。"""
    if not inverted_index:
        return ""
    word_positions = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions[pos] = word
    return " ".join(word_positions[i] for i in sorted(word_positions))


# ── Crossref 引擎 ──────────────────────────────────────────

CROSSREF_URL = "https://api.crossref.org/works"


def search_crossref(query: str, limit: int = 10) -> List[HybridPaper]:
    """通过 Crossref API 检索文献。"""
    papers = []
    try:
        params = {
            "query": query,
            "rows": min(limit, 50),
            "sort": "relevance",
        }
        r = requests.get(CROSSREF_URL, params=params, timeout=15,
                         headers={"User-Agent": "MCM-Agent/1.0"})
        r.raise_for_status()
        data = r.json()

        for item in data.get("message", {}).get("items", [])[:limit]:
            authors = []
            for auth in item.get("author", []):
                given = auth.get("given", "")
                family = auth.get("family", "")
                if given or family:
                    authors.append(f"{given} {family}".strip())

            doi = item.get("DOI", "")
            year = item.get("published-print", {}).get("date-parts", [[None]])[0][0]
            if not year:
                year = item.get("created", {}).get("date-parts", [[None]])[0][0]

            abstract = item.get("abstract", "")
            # 清理 HTML 标签
            abstract = re.sub(r'<[^>]+>', '', abstract) if abstract else ""

            papers.append(HybridPaper(
                title=item.get("title", [""])[0] if item.get("title") else "",
                authors=authors,
                year=year,
                doi=doi,
                abstract=abstract,
                citation_count=item.get("is-referenced-by-count", 0),
                source="crossref",
            ))
    except Exception as e:
        print(f"[Crossref] 检索出错: {e}", file=sys.stderr)

    return papers


# ── 结果融合与去重 ─────────────────────────────────────────

def _title_similarity(t1: str, t2: str) -> float:
    """计算两个标题的简单相似度（基于词重叠）。"""
    def tokenize(s):
        return set(re.findall(r'\w+', s.lower()))
    t1_tokens = tokenize(t1)
    t2_tokens = tokenize(t2)
    if not t1_tokens or not t2_tokens:
        return 0.0
    intersection = t1_tokens & t2_tokens
    union = t1_tokens | t2_tokens
    return len(intersection) / len(union)


def fuse_results(openalex_papers: List[HybridPaper],
                 crossref_papers: List[HybridPaper],
                 limit: int = 10) -> List[HybridPaper]:
    """融合双引擎结果：DOI 精确匹配 → 标题模糊匹配 → 去重排序。"""
    fused = []
    used_indices = set()

    # 第一轮：DOI 精确匹配（交叉验证）
    for i, oa in enumerate(openalex_papers):
        if not oa.doi:
            continue
        for j, cr in enumerate(crossref_papers):
            if j in used_indices:
                continue
            if cr.doi and oa.doi.lower() == cr.doi.lower():
                # 合并信息
                merged = HybridPaper(
                    title=oa.title or cr.title,
                    authors=oa.authors or cr.authors,
                    year=oa.year or cr.year,
                    doi=oa.doi,
                    abstract=oa.abstract or cr.abstract,
                    citation_count=max(oa.citation_count, cr.citation_count),
                    source="cross_validated",
                    cross_validated=True,
                )
                fused.append(merged)
                used_indices.add(j)
                break

    # 第二轮：标题模糊匹配
    remaining_cr = [p for j, p in enumerate(crossref_papers) if j not in used_indices]
    for oa in openalex_papers:
        if any(p is oa for p in fused):  # 已在 DOI 匹配中合并
            continue
        best_match = None
        best_sim = 0.0
        for j, cr in enumerate(remaining_cr):
            sim = _title_similarity(oa.title, cr.title)
            if sim > best_sim:
                best_sim = sim
                best_match = j
        if best_sim >= 0.85 and best_match is not None:
            cr = remaining_cr.pop(best_match)
            merged = HybridPaper(
                title=oa.title or cr.title,
                authors=oa.authors or cr.authors,
                year=oa.year or cr.year,
                doi=oa.doi or cr.doi,
                abstract=oa.abstract or cr.abstract,
                citation_count=max(oa.citation_count, cr.citation_count),
                source="cross_validated",
                cross_validated=True,
            )
            fused.append(merged)

    # 第三轮：添加剩余未匹配的文献
    seen_titles = {p.title.lower() for p in fused}
    for p in openalex_papers + crossref_papers:
        if p.title.lower() not in seen_titles:
            fused.append(p)
            seen_titles.add(p.title.lower())

    # 按引用次数排序
    fused.sort(key=lambda p: (p.cross_validated, p.citation_count), reverse=True)
    return fused[:limit]


# ── 相关性过滤 ─────────────────────────────────────────────

def filter_relevance(papers: List[HybridPaper], query: str,
                     min_term_matches: int = 2) -> List[HybridPaper]:
    """按查询词匹配数过滤低相关度文献。"""
    query_terms = set(re.findall(r'\w+', query.lower()))
    relevant = []
    for p in papers:
        title_terms = set(re.findall(r'\w+', p.title.lower()))
        matches = len(query_terms & title_terms)
        if matches >= min_term_matches:
            relevant.append(p)
    return relevant if relevant else papers  # 至少返回原始结果


# ── 主入口 ─────────────────────────────────────────────────

def search_papers(query: str, limit: int = 10,
                  min_term_matches: int = 2) -> List[HybridPaper]:
    """双引擎文献检索主函数。

    Parameters
    ----------
    query : str
        检索关键词。
    limit : int
        返回结果数量上限。
    min_term_matches : int
        标题中至少匹配的查询词数。

    Returns
    -------
    list of HybridPaper
    """
    if not HAS_REQUESTS:
        raise ImportError("需要安装 requests: pip install requests")

    # 并行检索
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_oa = executor.submit(search_openalex, query, limit * 2)
        future_cr = executor.submit(search_crossref, query, limit * 2)
        oa_results = future_oa.result()
        cr_results = future_cr.result()

    # 融合去重
    fused = fuse_results(oa_results, cr_results, limit)

    # 相关性过滤
    filtered = filter_relevance(fused, query, min_term_matches)

    return filtered[:limit]


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    if not HAS_REQUESTS:
        print("需要安装依赖: pip install requests")
        sys.exit(1)

    import argparse

    parser = argparse.ArgumentParser(
        description="双引擎学术文献检索（OpenAlex + Crossref）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               '  python hybrid_scholar.py "grey prediction model GM(1,1)"\n'
               '  python hybrid_scholar.py "entropy weight TOPSIS" --limit 5 --json',
    )
    parser.add_argument("query", type=str, help="检索关键词")
    parser.add_argument("--limit", type=int, default=10, help="返回结果数（默认 10）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    print(f"检索中: \"{args.query}\" ...")
    t0 = time.time()
    papers = search_papers(args.query, args.limit)
    elapsed = time.time() - t0

    if args.json:
        output = {
            "query": args.query,
            "elapsed_s": round(elapsed, 2),
            "total": len(papers),
            "results": [p.to_dict() for p in papers],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"找到 {len(papers)} 篇文献（{elapsed:.1f}s）\n")
        for i, p in enumerate(papers, 1):
            tag = "[✓] " if p.cross_validated else f"[{p.source[:2].upper()}] "
            print(f"{i:2d}. {tag}{p.title}")
            if p.authors:
                print(f"    作者: {', '.join(p.authors[:3])}"
                      f"{'...' if len(p.authors) > 3 else ''}")
            if p.year:
                print(f"    年份: {p.year}", end="")
            if p.citation_count:
                print(f" | 引用: {p.citation_count}", end="")
            if p.doi:
                print(f" | DOI: {p.doi}", end="")
            print()
            if p.abstract:
                abbr = p.abstract[:150].replace("\n", " ")
                print(f"    摘要: {abbr}...")
            print()
