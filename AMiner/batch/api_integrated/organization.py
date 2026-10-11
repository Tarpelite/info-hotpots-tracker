import csv
from itertools import islice
from pathlib import Path
from typing import Any, Iterable, Iterator

from .progress_bar import ProgressBar

if __package__ and __package__.startswith("AMiner."):
    from ... import api
else:  # 支持由 `AMiner/main.py` 直接导入
    import api

ORGID_PATH = Path(__file__).resolve().parents[2] / "data_cleaned" / "organization.csv"
PAPER_AUTHOR_PATH = (
    Path(__file__).resolve().parents[2] / "data_cleaned" / "paper_author.csv"
)


def _iter_unique_organizations(
    rows: Iterable[dict[str, str | None]],
) -> Iterator[str]:
    """按首次出现顺序合并 org 和 org_zh 中的非空机构名称。"""
    seen_organizations: set[str] = set()
    for row in rows:
        for column in ("org", "org_zh"):
            organization = (row.get(column) or "").strip()
            if not organization or organization in seen_organizations:
                continue
            seen_organizations.add(organization)
            yield organization


def query_organizations() -> Any:
    """从论文作者表中读取中英文机构名称并批量搜索机构。"""
    with PAPER_AUTHOR_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = set(reader.fieldnames or ())
        missing_columns = {"org", "org_zh"} - fieldnames
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"论文作者表缺少列 {missing}: {PAPER_AUTHOR_PATH}")

        organizations = list(_iter_unique_organizations(reader))

    if not organizations:
        return []

    results: list[object] = []
    batch_size = 20
    batch_count = (len(organizations) + batch_size - 1) // batch_size
    with ProgressBar(batch_count, label="机构查询进度") as progress:
        for batch_number, i in enumerate(
            range(0, len(organizations), batch_size), start=1
        ):
            batch = organizations[i : i + batch_size]
            results.append(api.search_organizations(batch))
            progress.update(batch_number)
    return results


def _iter_unique_orgids(
    rows: Iterable[dict[str, str | None]],
) -> Iterator[str]:
    """按首次出现顺序返回非空且不重复的 org_id。"""
    seen_orgids: set[str] = set()
    for row in rows:
        orgid = (row.get("org_id") or "").strip()
        if not orgid or orgid in seen_orgids:
            continue
        seen_orgids.add(orgid)
        yield orgid


def query_organization_detail(count: int | None = None) -> Any:
    """从论文与机构对应表中提取唯一机构，并批量查询机构详情。

    Args:
        count: 要查询的唯一机构数量（即传入接口的 orgid 列表长度）。
            为 None 时查询 CSV 中的全部机构；
            为 0 时不发起查询并返回空列表。

    Returns:
        详情接口对整个 orgid 列表的返回值。
    """
    if count is not None and (not isinstance(count, int) or isinstance(count, bool)):
        raise ValueError("count 必须是整数或 None")
    if count is not None and count < 0:
        raise ValueError("count 不能小于 0")

    with ORGID_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None or "org_id" not in reader.fieldnames:
            raise ValueError(f"机构列表缺少 org_id 列: {ORGID_PATH}")

        org_ids = _iter_unique_orgids(reader)
        if count is not None:
            org_ids = islice(org_ids, count)
        id_list = list(org_ids)

    if not id_list:
        return []
    with ProgressBar(1, label="机构详情查询进度") as progress:
        result = api.get_organization_detail(id_list)
        progress.update(1)
    return result
