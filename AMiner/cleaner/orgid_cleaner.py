#!/usr/bin/env python3
"""从论文详情 CSV 的 authors 列提取并去重机构 ID。"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path
from typing import Any, Sequence


AMINER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = AMINER_DIR / "data_cleaned" / "paper_detail_cleaned.csv"
DEFAULT_OUTPUT_PATH = AMINER_DIR / "data_cleaned" / "orgid_cleaned.csv"


def _parse_authors(raw_authors: str, row_number: int) -> list[Any]:
    """解析 authors 单元格，并在数据格式异常时给出对应 CSV 行号。"""
    if not raw_authors.strip():
        return []

    try:
        authors = json.loads(raw_authors)
    except json.JSONDecodeError as exc:
        raise ValueError(f"CSV 第 {row_number} 行的 authors 不是有效 JSON: {exc}") from exc

    if not isinstance(authors, list):
        raise ValueError(f"CSV 第 {row_number} 行的 authors 应为 JSON 数组")
    return authors


def extract_unique_orgids(input_path: Path) -> tuple[list[str], int, int, int]:
    """返回去重后的 orgid，以及论文行数、作者数和重复 orgid 数量。"""
    unique_orgids: list[str] = []
    seen_orgids: set[str] = set()
    paper_count = 0
    author_count = 0
    duplicate_count = 0

    try:
        file = input_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise OSError(f"无法读取 CSV 文件 {input_path}: {exc}") from exc

    with file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"{input_path} 缺少表头")
        if "authors" not in reader.fieldnames:
            raise ValueError(f"{input_path} 缺少 authors 列")

        for row_number, row in enumerate(reader, start=2):
            paper_count += 1
            for author_index, author in enumerate(
                _parse_authors(row.get("authors") or "", row_number), start=1
            ):
                author_count += 1
                if not isinstance(author, dict):
                    raise ValueError(
                        f"CSV 第 {row_number} 行的第 {author_index} 个作者不是 JSON 对象"
                    )

                raw_orgid = author.get("orgid")
                if raw_orgid is None:
                    continue
                if not isinstance(raw_orgid, (str, int)) or isinstance(raw_orgid, bool):
                    raise ValueError(
                        f"CSV 第 {row_number} 行的第 {author_index} 个 orgid "
                        "应为字符串或整数"
                    )

                orgid = str(raw_orgid).strip()
                if not orgid:
                    continue
                if orgid in seen_orgids:
                    duplicate_count += 1
                    continue

                seen_orgids.add(orgid)
                unique_orgids.append(orgid)

    return unique_orgids, paper_count, author_count, duplicate_count


def write_orgids(orgids: Sequence[str], output_path: Path) -> None:
    """以 UTF-8 BOM 原子写入单列 orgid CSV。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            writer = csv.writer(file)
            writer.writerow(["orgid"])
            writer.writerows((orgid,) for orgid in orgids)
        temporary_path.replace(output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def clean_orgids(input_path: Path, output_path: Path) -> tuple[int, int, int, int]:
    orgids, paper_count, author_count, duplicate_count = extract_unique_orgids(
        input_path
    )
    write_orgids(orgids, output_path)
    return paper_count, author_count, len(orgids), duplicate_count


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 paper_detail_cleaned.csv 的 authors 列提取并去重 orgid",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"输入 CSV 路径（默认: {DEFAULT_INPUT_PATH}）",
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
        paper_count, author_count, unique_count, duplicate_count = clean_orgids(
            args.input, args.output
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"清洗失败: {exc}") from exc

    print(
        f"清洗完成: 扫描论文 {paper_count} 条、作者 {author_count} 人，"
        f"提取唯一 orgid {unique_count} 个，移除重复 {duplicate_count} 个"
    )
    print(f"CSV 已保存到: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
