import csv
from itertools import islice
from pathlib import Path
from typing import Any

if __package__ and __package__.startswith("AMiner."):
    from ... import api
else:  # 支持由 `AMiner/main.py` 直接导入
    import api

ORGID_PATH = Path(__file__).resolve().parents[2] / "data_cleaned" / "orgid_cleaned.csv"

def query_organization_detail(count: int | None = None) -> Any:
    """按清洗后组织列表中的顺序批量查询机构详情。

    Args:
        count: 要查询的机构数量（即传入接口的 orgid 列表长度）。
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
        if reader.fieldnames is None or "orgid" not in reader.fieldnames:
            raise ValueError(f"机构列表缺少 orgid 列: {ORGID_PATH}")

        org_ids = (
            org_id
            for row in reader
            if (org_id := (row.get("orgid") or "").strip())
        )
        if count is not None:
            org_ids = islice(org_ids, count)
        id_list = list(org_ids)

    if not id_list:
        return []
    return api.get_organization_detail(id_list)