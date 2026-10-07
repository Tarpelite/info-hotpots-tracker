from typing import Any

from .aminer_client import AMinerClient
from ._utils import client_or_default, compact_dict, optional_int, require_text, require_text_list


def search_persons(
    name: str,
    size: int | None = None,
    page: int | None = None,
    orgs: list[str] | None = None,
    client: AMinerClient | None = None,
) -> Any:
    """学者搜索：POST /api/person/search。"""
    payload = compact_dict(
        {
            "name": require_text(name, "name"),
            "size": optional_int(size, "size", min_value=1),
            "page": optional_int(page, "page", min_value=0),
            "orgs": require_text_list(orgs, "orgs") if orgs is not None else None,
        }
    )
    return client_or_default(client).post("/api/person/search", payload=payload)


def get_person_detail(*args: Any, **kwargs: Any) -> Any:
    """学者详情：GET /api/person/detail。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_person_papers(*args: Any, **kwargs: Any) -> Any:
    """学者论文：GET /api/person/paper/relation。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_person_patents(*args: Any, **kwargs: Any) -> Any:
    """学者专利：GET /api/person/patent/relation。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_person_figure(*args: Any, **kwargs: Any) -> Any:
    """学者画像：GET /api/person/figure。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")
