import argparse
import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .api import paper
except ImportError:  # 支持直接执行 `python AMiner/main.py`
    from api import paper


PAPER_KEYWORDS = [
    "生命科学",
    "材料化学",
    "高能物理",
    "量子科技",
    "集成电路",
    "新型电力系统",
    "航空航天",
]

DEFAULT_PAGE = 0
DEFAULT_SIZE = 10
DEFAULT_MAX_PAGES = 1


def query_paper_lists(
    size: int = DEFAULT_SIZE,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> dict[str, list[object]]:
    """按单个关键词分别查询论文列表，每个关键词从第 0 页开始。"""
    results = {}

    for keyword in PAPER_KEYWORDS:
        page = DEFAULT_PAGE
        keyword_results = []

        for _ in range(max_pages):
            keyword_results.append(
                api.paper.get_paper_list(
                    keywords=[keyword],
                    page=page,
                    size=size,
                )
            )
            page += 1

        results[keyword] = keyword_results

    return results


def main():
    """主函数。"""
    return query_paper_lists()


def _iter_papers(value: Any) -> Iterator[dict[str, Any]]:
    """从 AMiner 的分页响应中提取论文对象。

    不同版本的接口会把数组放在 ``data``、``items``、``records`` 或
    ``results`` 下；保留这个适配层可以避免把 API 的分页包装写死在导入器中。
    """
    if isinstance(value, list):
        for item in value:
            yield from _iter_papers(item)
        return

    if not isinstance(value, Mapping):
        return

    if any(value.get(key) for key in ("id", "_id", "paper_id")):
        yield dict(value)
        return

    for key in ("data", "items", "records", "results", "papers", "list", "content", "rows", "hits", "docs"):
        nested = value.get(key)
        if nested is not None and nested is not value:
            yield from _iter_papers(nested)


def flatten_paper_results(results: Mapping[str, list[Any]]) -> list[dict[str, Any]]:
    """将按关键词、按页的结果去重为论文数组。"""
    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for pages in results.values():
        for page_result in pages:
            for paper_record in _iter_papers(page_result):
                paper_id = paper_record.get("id") or paper_record.get("_id") or paper_record.get("paper_id")
                if paper_id is None:
                    continue
                paper_id = str(paper_id)
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)
                papers.append(paper_record)
    return papers


def import_papers_to_worker(
    papers: list[dict[str, Any]],
    import_url: str,
    chunk_size: int = 100,
    timeout: float = 30,
) -> int:
    """通过 Worker 的 D1 binding 批量写入论文，返回写入记录数。"""
    if not import_url.strip():
        raise ValueError("import_url 不能为空")
    if chunk_size < 1:
        raise ValueError("chunk_size 必须大于 0")

    upserted = 0
    for start in range(0, len(papers), chunk_size):
        chunk = papers[start : start + chunk_size]
        request = Request(
            import_url,
            data=json.dumps({"papers": chunk}, ensure_ascii=False).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Worker 导入失败（HTTP {exc.code}）: {error_body}") from exc
        except URLError as exc:
            raise RuntimeError(f"无法连接 Worker 导入接口: {exc.reason}") from exc

        try:
            result = json.loads(response_body) if response_body else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Worker 返回了非法 JSON: {response_body[:200]}") from exc
        if result.get("ok") is not True:
            raise RuntimeError(f"Worker 导入失败: {result}")
        upserted += int(result.get("upserted", len(chunk)))
    return upserted


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取 AMiner 论文并导入 Worker 本地 D1")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE, help="每个关键词每页抓取数量")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="每个关键词抓取页数")
    parser.add_argument("--import-url", help="Worker 导入接口，例如 http://127.0.0.1:8787/api/papers/import")
    parser.add_argument("--output", type=Path, help="可选：将原始结果和去重后的论文保存为 JSON")
    parser.add_argument("--chunk-size", type=int, default=100, help="每次 POST 给 Worker 的论文数量")
    return parser.parse_args()


def cli() -> int:
    args = _parse_args()
    if args.size < 1 or args.max_pages < 1:
        raise SystemExit("--size 和 --max-pages 必须大于 0")

    results = query_paper_lists(size=args.size, max_pages=args.max_pages)
    papers = flatten_paper_results(results)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps({"results": results, "papers": papers}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    upserted = 0
    if args.import_url:
        upserted = import_papers_to_worker(papers, args.import_url, chunk_size=args.chunk_size)

    print(json.dumps({"keywords": len(results), "papers": len(papers), "upserted": upserted}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
