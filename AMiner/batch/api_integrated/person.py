import csv
import math
import time
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .progress_bar import ProgressBar

if __package__ and __package__.startswith("AMiner."):
    from ... import api
else:  # 支持由 `AMiner/main.py` 直接导入
    import api

PAPER_AUTHOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "data_cleaned"
    / "paper_author_cleaned.csv"
)


def _iter_unique_person_queries(
    rows: Iterable[dict[str, str | None]],
) -> Iterator[tuple[str, str | None]]:
    """按首次出现顺序返回唯一的姓名与机构查询条件。"""
    seen_queries: set[tuple[str, str]] = set()
    for row in rows:
        name = (row.get("name_zh") or "").strip() or (
            row.get("name") or ""
        ).strip()
        if not name:
            continue

        organization = (row.get("org_zh") or "").strip() or (
            row.get("org") or ""
        ).strip()
        query_key = (name, organization)
        if query_key in seen_queries:
            continue

        seen_queries.add(query_key)
        yield name, organization or None


def query_persons(request_interval: float = 0.2) -> list[Any]:
    """读取论文作者并逐个搜索学者，默认在请求之间间隔 0.2 秒。"""
    if (
        isinstance(request_interval, bool)
        or not isinstance(request_interval, (int, float))
        or not math.isfinite(request_interval)
        or request_interval < 0
    ):
        raise ValueError("request_interval 必须是非负有限数")

    with PAPER_AUTHOR_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = set(reader.fieldnames or ())
        required_columns = {"name", "name_zh", "org", "org_zh"}
        missing_columns = required_columns - fieldnames
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"论文作者表缺少列 {missing}: {PAPER_AUTHOR_PATH}")

        queries = list(_iter_unique_person_queries(reader))

    results: list[Any] = []
    total = len(queries)
    with ProgressBar(total, label="学者查询进度") as progress:
        for completed, (name, organization) in enumerate(queries, start=1):
            results.append(
                api.search_persons(name=name, org=organization, size=10)
            )
            progress.update(completed)
            if completed < total and request_interval > 0:
                time.sleep(request_interval)

    return results
