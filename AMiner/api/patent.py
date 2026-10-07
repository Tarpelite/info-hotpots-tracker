from typing import Any

from .aminer_client import AMinerClient
from ._utils import client_or_default, compact_dict, optional_int, require_text


def search_patents(
    query: str,
    page: int | None = None,
    size: int | None = None,
    client: AMinerClient | None = None,
) -> Any:
    """专利搜索：POST /api/patent/search。"""
    payload = compact_dict(
        {
            "query": require_text(query, "query"),
            "page": optional_int(page, "page", min_value=0),
            "size": optional_int(size, "size", min_value=1),
        }
    )
    return client_or_default(client).post("/api/patent/search", payload=payload)


def get_patent_info(*args: Any, **kwargs: Any) -> Any:
    """专利信息：GET /api/patent/info。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_patent_detail(*args: Any, **kwargs: Any) -> Any:
    """专利详情：GET /api/patent/detail。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")
