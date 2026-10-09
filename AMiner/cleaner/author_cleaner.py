#!/usr/bin/env python3
"""从论文详情 CSV 提取论文 ID 及其作者信息。"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Sequence

AMINER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = AMINER_DIR / "data_cleaned" / "paper_detail_cleaned.csv"
DEFAULT_OUTPUT_PATH = AMINER_DIR / "data_cleaned" / "paper_author_cleaned.csv"


def _parse_authors(raw_authors: str, row_number: int) -> list[Any]:
    """解析 authors 单元格，并在数据格式异常时给出对应 CSV 行号。"""
    if not raw_authors.strip():
        return []

    try:
        authors = json.loads(raw_authors)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"CSV 第 {row_number} 行的 authors 不是有效 JSON: {exc}"
        ) from exc

    if not isinstance(authors, list):
        raise ValueError(f"CSV 第 {row_number} 行的 authors 应为 JSON 数组")
    return authors


def _string_value(author: dict[str, Any], field: str) -> str:
    """将缺失或值为 null 的作者字段转换为空字符串。"""
    value = author.get(field)
    return "" if value is None else str(value).strip()


def _first_segment(value: str) -> str:
    """仅保留第一个逗号（半角/全角）之前的内容，无逗号则原样返回。"""
    positions = [pos for pos in (value.find(","), value.find("，")) if pos != -1]
    if not positions:
        return value
    return value[: min(positions)].strip()


def extract_paper_authors(
    input_path: Path,
) -> tuple[list[tuple[str, str, str, str, str]], int, int]:
    """返回 (paperid, name, name_zh, org, org_zh) 作者记录及统计。"""
    author_rows: list[tuple[str, str, str, str, str]] = []
    paper_count = 0
    author_count = 0

    try:
        file = input_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise OSError(f"无法读取 CSV 文件 {input_path}: {exc}") from exc

    with file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"{input_path} 缺少表头")
        missing_fields = {"id", "authors"}.difference(reader.fieldnames)
        if missing_fields:
            names = "、".join(sorted(missing_fields))
            raise ValueError(f"{input_path} 缺少 {names} 列")

        for row_number, row in enumerate(reader, start=2):
            paper_count += 1
            paperid = (row.get("id") or "").strip()
            for author_index, author in enumerate(
                _parse_authors(row.get("authors") or "", row_number), start=1
            ):
                author_count += 1
                if not isinstance(author, dict):
                    raise ValueError(
                        f"CSV 第 {row_number} 行的第 {author_index} 个作者不是 JSON 对象"
                    )

                author_rows.append(
                    (
                        paperid,
                        _string_value(author, "name"),
                        _string_value(author, "name_zh"),
                        _first_segment(_string_value(author, "org")),
                        _first_segment(_string_value(author, "org_zh")),
                    )
                )

    return author_rows, paper_count, author_count


def write_paper_authors(
    author_rows: Sequence[tuple[str, str, str, str, str]], output_path: Path
) -> None:
    """以 UTF-8 BOM 原子写入论文 ID 与作者信息 CSV。"""
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
            writer.writerow(["paperid", "name", "name_zh", "org", "org_zh"])
            writer.writerows(author_rows)
        try:
            temporary_path.replace(output_path)
        except PermissionError:
            # Windows 上目标文件被读取时可能允许覆盖、但不允许原子替换。
            shutil.copyfile(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def clean_paper_authors(input_path: Path, output_path: Path) -> tuple[int, int]:
    author_rows, paper_count, author_count = extract_paper_authors(input_path)
    write_paper_authors(author_rows, output_path)
    return paper_count, author_count


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 paper_detail_cleaned.csv 提取论文 ID 与作者信息",
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
        paper_count, author_count = clean_paper_authors(args.input, args.output)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"清洗失败: {exc}") from exc

    print(
        f"清洗完成: 扫描论文 {paper_count} 条、作者 {author_count} 人，"
        f"写入作者记录 {author_count} 条"
    )
    print(f"CSV 已保存到: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
