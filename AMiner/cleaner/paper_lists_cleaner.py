#!/usr/bin/env python3
"""将 AMiner 分页论文查询结果合并为结构化 CSV。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Sequence


AMINER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = AMINER_DIR / "data" / "query_paper_lists"
DEFAULT_OUTPUT_PATH = AMINER_DIR / "data_cleaned" / "paper_lists_cleaned.csv"
INPUT_PATTERN = "query_paper_lists_*.json"

PROVENANCE_FIELDS = ("source_file", "query_keywords", "page_index")
PREFERRED_PAPER_FIELDS = (
    "id",
    "doi",
    "title",
    "title_zh",
    "abstract",
    "abstract_zh",
    "keywords",
    "keywords_zh",
    "year",
)


def _extract_query_keywords(path: Path) -> list[str]:
    """从 main.py 生成的文件名中恢复查询关键词。"""
    match = re.search(r"_keywords_\[_([^]]*?)_\]", path.stem)
    if not match:
        return []
    return [keyword for keyword in match.group(1).split("_,_") if keyword]


def _load_pages(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON 文件 {path}: {exc}") from exc

    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError(f"{path} 的顶层结构应为分页响应数组")

    pages: list[dict[str, Any]] = []
    for page_index, page in enumerate(payload):
        if not isinstance(page, dict):
            raise ValueError(f"{path} 第 {page_index} 页不是 JSON 对象")
        pages.append(page)
    return pages


def collect_papers(input_files: Sequence[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    """读取所有输入文件，返回论文行和发现的论文字段。"""
    rows: list[dict[str, Any]] = []
    paper_fields: set[str] = set()

    for input_path in input_files:
        query_keywords = _extract_query_keywords(input_path)
        for page_index, page in enumerate(_load_pages(input_path)):
            code = page.get("code")
            if page.get("success") is False or (code is not None and code != 200):
                message = page.get("msg") or "未知错误"
                raise ValueError(
                    f"{input_path} 第 {page_index} 页请求失败: "
                    f"code={code!r}, msg={message!r}"
                )

            papers = page.get("data", [])
            if papers is None:
                papers = []
            if not isinstance(papers, list):
                raise ValueError(f"{input_path} 第 {page_index} 页的 data 不是数组")

            for record_index, paper in enumerate(papers):
                if not isinstance(paper, dict):
                    raise ValueError(
                        f"{input_path} 第 {page_index} 页第 {record_index} 条论文不是对象"
                    )
                collisions = set(paper).intersection(PROVENANCE_FIELDS)
                if collisions:
                    names = ", ".join(sorted(collisions))
                    raise ValueError(f"论文数据包含保留字段: {names}")

                paper_fields.update(paper)
                rows.append(
                    {
                        "source_file": input_path.name,
                        "query_keywords": query_keywords,
                        "page_index": page_index,
                        **paper,
                    }
                )

    preferred = [field for field in PREFERRED_PAPER_FIELDS if field in paper_fields]
    extra = sorted(paper_fields.difference(preferred))
    return rows, [*PROVENANCE_FIELDS, *preferred, *extra]


def deduplicate_papers_by_id(
    rows: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """按非空论文 ID 去重，保留输入顺序中首次出现的记录。"""
    unique_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    duplicate_count = 0

    for row in rows:
        raw_id = row.get("id")
        paper_id = str(raw_id).strip() if raw_id is not None else ""
        if not paper_id:
            unique_rows.append(row)
            continue
        if paper_id in seen_ids:
            duplicate_count += 1
            continue

        seen_ids.add(paper_id)
        unique_rows.append(row)

    return unique_rows, duplicate_count


def _serialize_cell(value: Any) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, (list, dict, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, (str, int, float)):
        return value
    return str(value)


def write_csv(rows: Sequence[dict[str, Any]], fieldnames: Sequence[str], output: Path) -> None:
    """以 UTF-8 BOM 原子写入 CSV，兼容 Excel 直接打开中文。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {field: _serialize_cell(row.get(field)) for field in fieldnames}
                )
        temporary_path.replace(output)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def clean_paper_lists(data_dir: Path, output: Path) -> tuple[int, int, int]:
    input_files = sorted(data_dir.glob(INPUT_PATTERN), key=lambda path: path.name)
    if not input_files:
        raise FileNotFoundError(f"{data_dir} 中没有匹配 {INPUT_PATTERN} 的文件")

    rows, fieldnames = collect_papers(input_files)
    unique_rows, duplicate_count = deduplicate_papers_by_id(rows)
    write_csv(unique_rows, fieldnames, output)
    return len(input_files), len(rows), duplicate_count


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="合并 AMiner/data/query_paper_lists_*.json 并生成 CSV",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"JSON 数据目录（默认: {DEFAULT_DATA_DIR}）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"输出 CSV 路径（默认: {DEFAULT_OUTPUT_PATH}）",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        file_count, row_count, duplicate_count = clean_paper_lists(
            args.data_dir, args.output
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"清洗失败: {exc}") from exc

    print(
        f"清洗完成: {file_count} 个 JSON 文件，原始记录 {row_count} 条，"
        f"按 ID 去重后 {row_count - duplicate_count} 条，移除重复 {duplicate_count} 条"
    )
    print(f"CSV 已保存到: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
