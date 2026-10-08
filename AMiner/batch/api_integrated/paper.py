import csv
from itertools import islice
from pathlib import Path

if __package__ and __package__.startswith("AMiner."):
    from ... import api
else:  # 支持由 `AMiner/main.py` 直接导入
    import api

DEFAULT_PAGE = 0
DEFAULT_SIZE = 10
DEFAULT_MAX_PAGES = 1
PAPER_LISTS_PATH = Path(__file__).resolve().parents[2] / "data_cleaned" / "paper_lists_cleaned.csv"

def query_paper_lists(
    size: int = DEFAULT_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
    keywords: list[str] | None = None,
) -> list[object]:
    """将传入的关键词列表作为一个整体进行查询，从第 0 页开始。

    Args:
        size: 每页返回的论文数量，必须大于 0。
        max_pages: 最多查询的页数，必须大于 0。
        keywords: 作为一个整体参与查询的关键词列表；为 None 或空时抛出 ValueError。

    Returns:
        各页查询结果组成的列表，每个元素对应一页的返回结果。
    """
    if size < 1:
        raise ValueError("size 必须大于 0")
    if max_pages < 1:
        raise ValueError("max_pages 必须大于 0")
    if not keywords:
        raise ValueError("keywords 不能为空")

    results: list[object] = []
    for page in range(DEFAULT_PAGE, DEFAULT_PAGE + max_pages):
        results.append(
            api.paper.get_papers_by_keywords(
                keywords=keywords,
                page=page,
                size=size,
            )
        )
    return results

def query_paper_detail(count: int | None = None) -> list[object]:
    """按清洗后论文列表中的顺序批量查询论文详情。

    Args:
        count: 要查询的论文数量。为 None 时查询 CSV 中的全部论文；
            为 0 时不发起查询并返回空列表。

    Returns:
        每篇论文的详情接口返回值组成的列表。
    """
    if count is not None and (not isinstance(count, int) or isinstance(count, bool)):
        raise ValueError("count 必须是整数或 None")
    if count is not None and count < 0:
        raise ValueError("count 不能小于 0")

    with PAPER_LISTS_PATH.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None or "id" not in reader.fieldnames:
            raise ValueError(f"论文列表缺少 id 列: {PAPER_LISTS_PATH}")

        paper_ids = (
            paper_id
            for row in reader
            if (paper_id := (row.get("id") or "").strip())
        )
        if count is not None:
            paper_ids = islice(paper_ids, count)

        return [api.get_paper_detail(paper_id) for paper_id in paper_ids]
