from typing import Any

from .aminer_client import AMinerClient
from ._utils import client_or_default, compact_dict, optional_int, require_text


def search_venues(name: str, client: AMinerClient | None = None) -> Any:
    """期刊搜索：POST /api/venue/search。"""
    payload = {"name": require_text(name, "name")}
    return client_or_default(client).post("/api/venue/search", payload=payload)


def get_venue_detail(*args: Any, **kwargs: Any) -> Any:
    """期刊详情：POST /api/venue/detail。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_venue_papers(
    venue_id: str,
    offset: int | None = None,
    limit: int | None = None,
    year: int | None = None,
    client: AMinerClient | None = None,
) -> Any:
    """期刊论文：POST /api/venue/paper/relation。"""
    payload = compact_dict(
        {
            "id": require_text(venue_id, "id"),
            "offset": optional_int(offset, "offset", min_value=0),
            "limit": optional_int(limit, "limit", min_value=1),
            "year": optional_int(year, "year", min_value=0),
        }
    )
    return client_or_default(client).post("/api/venue/paper/relation", payload=payload)
