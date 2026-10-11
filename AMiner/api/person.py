from typing import Any

from .aminer_client import AMinerClient
from ._utils import client_or_default, compact_dict, optional_int, require_text, require_text_list


def search_persons(
    name: str | None = None,
    offset: int | None = None,
    org: str | None = None,
    size: int | None = None,
    org_id: list[str] | None = None,
    client: AMinerClient | None = None,
) -> Any:
    """学者搜索：POST /person/search。"""
    payload = compact_dict(
        {
            "name": require_text(name, "name") if name is not None else None,
            "offset": optional_int(offset,"offset",min_value=0,max_value=20,),
            "org": require_text(org, "org") if org is not None else None,
            "size": optional_int(size,"size",min_value=1,max_value=10,),
            "org_id": (require_text_list(org_id, "org_id") if org_id is not None else None),
        }
    )
    return client_or_default(client).post("/person/search", payload=payload)


def get_person_detail(id: str, client: AMinerClient | None = None) -> Any:
    """学者详情：GET /person/detail。"""
    params = compact_dict({"id": require_text(id, "id")})
    return client_or_default(client).get("/person/detail", params=params)


def get_person_papers(*args: Any, **kwargs: Any) -> Any:
    """学者论文：GET /person/paper/relation。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_person_patents(*args: Any, **kwargs: Any) -> Any:
    """学者专利：GET /person/patent/relation。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_person_figure(*args: Any, **kwargs: Any) -> Any:
    """学者画像：GET /person/figure。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")
