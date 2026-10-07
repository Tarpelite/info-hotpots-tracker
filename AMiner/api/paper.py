from typing import Any

from .aminer_client import AMinerClient
from ._utils import (
    client_or_default,
    compact_dict,
    json_array_string,
    optional_bool,
    optional_int,
    optional_text,
    require_exactly_one_present,
    require_int,
    require_one_present,
    require_text,
    require_text_list,
)


def search_papers(
    title: str,
    page: int | None = 1,
    size: int | None = None,
    client: AMinerClient | None = None,
) -> Any:
    """论文搜索：GET /api/paper/search。"""
    params = compact_dict(
        {
            "title": require_text(title, "title"),
            "page": optional_int(page, "page", min_value=0),
            "size": optional_int(size, "size", min_value=1),
        }
    )
    return client_or_default(client).get("/api/paper/search", params=params)


def search_papers_pro(
    page: int | None = None,
    size: int | None = None,
    title: str | None = None,
    keyword: str | None = None,
    abstract: str | None = None,
    author: str | None = None,
    org: str | None = None,
    venue: str | None = None,
    order: str | None = None,
    client: AMinerClient | None = None,
) -> Any:
    """论文搜索 Pro：GET /api/paper/search/pro。"""
    if order is not None and order not in {"year", "n_citation"}:
        raise ValueError("参数 order 只能为 year 或 n_citation")

    params = compact_dict(
        {
            "page": optional_int(page, "page", min_value=0),
            "size": optional_int(size, "size", min_value=1, max_value=100),
            "title": optional_text(title, "title"),
            "keyword": optional_text(keyword, "keyword"),
            "abstract": optional_text(abstract, "abstract"),
            "author": optional_text(author, "author"),
            "org": optional_text(org, "org"),
            "venue": optional_text(venue, "venue"),
            "order": order,
        }
    )
    return client_or_default(client).get("/api/paper/search/pro", params=params)


def qa_search_papers(
    query: str | None = None,
    topic_high: Any | None = None,
    topic_middle: Any | None = None,
    topic_low: Any | None = None,
    use_topic: bool | None = None,
    size: int | None = None,
    year: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    citation_sort: bool | None = None,
    client: AMinerClient | None = None,
) -> Any:
    """论文问答搜索：POST /api/paper/qa/search。"""
    raw_payload = {
        "query": query,
        "topic_high": topic_high,
        "topic_middle": topic_middle,
        "topic_low": topic_low,
    }
    require_one_present(raw_payload, ("query", "topic_high"), "query 与 topic_high 至少需要传入一个")
    if any(raw_payload.get(name) is not None for name in ("topic_high", "topic_middle", "topic_low")):
        if use_topic is None:
            raise ValueError("使用 topic_* 参数时必须传入 use_topic")

    payload = compact_dict(
        {
            "query": optional_text(query, "query"),
            "topic_high": json_array_string(topic_high, "topic_high"),
            "topic_middle": json_array_string(topic_middle, "topic_middle"),
            "topic_low": json_array_string(topic_low, "topic_low"),
            "use_topic": optional_bool(use_topic, "use_topic"),
            "size": optional_int(size, "size", min_value=1),
            "year": optional_int(year, "year", min_value=0),
            "year_from": optional_int(year_from, "year_from", min_value=0),
            "year_to": optional_int(year_to, "year_to", min_value=0),
            "citation_sort": optional_bool(citation_sort, "citation_sort"),
        }
    )
    return client_or_default(client).post("/api/paper/qa/search", payload=payload)


def get_paper_info(ids: list[str], client: AMinerClient | None = None) -> Any:
    """论文信息（批量）：POST /api/paper/info。"""
    payload = {"ids": require_text_list(ids, "ids", max_items=100)}
    return client_or_default(client).post("/api/paper/info", payload=payload)


def get_paper_detail(paper_id: str, client: AMinerClient | None = None) -> Any:
    """论文详情：GET /api/paper/detail。"""
    params = {"id": require_text(paper_id, "id")}
    return client_or_default(client).get("/api/paper/detail", params=params)


def get_paper_relation(paper_id: str, client: AMinerClient | None = None) -> Any:
    """论文引用：GET /api/paper/relation。"""
    params = {"id": require_text(paper_id, "id")}
    return client_or_default(client).get("/api/paper/relation", params=params)


def search_papers_by_venue(
    page: int,
    size: int,
    keyword: str | None = None,
    venue: str | None = None,
    author: str | None = None,
    order: str | None = None,
    client: AMinerClient | None = None,
) -> Any:
    """按期刊组合搜索论文：GET /api/paper/list/by/search/venue。"""
    raw_params = {"keyword": keyword, "venue": venue, "author": author}
    require_exactly_one_present(
        raw_params,
        ("keyword", "venue", "author"),
        "keyword、venue、author 三者必须且只能传入一个",
    )
    if order is not None and order not in {"year", "n_citation"}:
        raise ValueError("参数 order 只能为 year 或 n_citation")

    params = compact_dict(
        {
            "keyword": optional_text(keyword, "keyword"),
            "venue": optional_text(venue, "venue"),
            "author": optional_text(author, "author"),
            "page": require_int(page, "page", min_value=0),
            "size": require_int(size, "size", min_value=1),
            "order": order,
        }
    )
    return client_or_default(client).get("/api/paper/list/by/search/venue", params=params)


def list_papers_by_keywords(
    keywords: list[str],
    page: int,
    size: int,
    client: AMinerClient | None = None,
) -> Any:
    """按关键词批量查询论文：GET /api/paper/list/citation/by/keywords。"""
    params = {
        "keywords": require_text_list(keywords, "keywords"),
        "page": require_int(page, "page", min_value=0),
        "size": require_int(size, "size", min_value=1),
    }
    return client_or_default(client).get("/api/paper/list/citation/by/keywords", params=params)


def get_paper_list(
    keywords: list[str],
    page: int,
    size: int,
    client: AMinerClient | None = None,
) -> Any:
    """兼容旧函数名：按关键词批量查询论文。"""
    return list_papers_by_keywords(keywords=keywords, page=page, size=size, client=client)


def get_paper_detail_by_year_org_venue(*args: Any, **kwargs: Any) -> Any:
    """按年份/期刊查询论文详情：GET /api/paper/platform/allpubs/more/detail/by/ts/org/venue。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")
