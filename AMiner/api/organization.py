from typing import Any

from .aminer_client import AMinerClient
from ._utils import client_or_default, require_text_list


def search_organizations(orgs: list[str], client: AMinerClient | None = None) -> Any:
    """机构搜索：POST /organization/search。"""
    payload = {"orgs": require_text_list(orgs, "orgs")}
    return client_or_default(client).post("/organization/search", payload=payload)


def get_organization_detail(ids: list[str], client: AMinerClient | None = None) -> Any:
    """机构详情：POST /organization/detail。"""
    payload = {"ids": require_text_list(ids, "ids")}
    return client_or_default(client).post("/organization/detail", payload=payload)


def get_organization_patents(*args: Any, **kwargs: Any) -> Any:
    """机构专利：GET /organization/patent/relation。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_organization_persons(*args: Any, **kwargs: Any) -> Any:
    """机构学者：GET /organization/person/relation。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def get_organization_papers(*args: Any, **kwargs: Any) -> Any:
    """机构论文：GET /organization/paper/relation。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def disambiguate_organization(*args: Any, **kwargs: Any) -> Any:
    """机构消歧：POST /organization/na。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")


def disambiguate_organization_pro(*args: Any, **kwargs: Any) -> Any:
    """机构消歧 Pro：POST /organization/na/pro。"""
    raise NotImplementedError("README 未提供完整参数规范，暂只保留函数名。")
