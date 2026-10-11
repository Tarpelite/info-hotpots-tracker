#!/usr/bin/env python3
"""清洗 AMiner 学者查询响应，输出人员记录 CSV。"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Sequence

AMINER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_PATH = AMINER_DIR / "data" / "query_persons" / "query_persons.json"
DEFAULT_OUTPUT_PATH = AMINER_DIR / "data_cleaned" / "persons_cleaned.csv"
OUTPUT_FIELDS = (
    "id",
    "name",
    "name_zh",
    "org",
    "org_zh",
    "org_id",
    "nation",
    "n_citation",
    "interests",
)


def _load_responses(input_path: Path) -> list[dict[str, Any]]:
    """读取接口响应数组或单个接口响应对象。"""
    try:
        with input_path.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON 文件 {input_path}: {exc}") from exc

    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError(f"{input_path} 的顶层结构应为接口响应数组或对象")

    responses: list[dict[str, Any]] = []
    for response_index, response in enumerate(payload):
        if not isinstance(response, dict):
            raise ValueError(f"{input_path} 第 {response_index} 个响应不是 JSON 对象")
        responses.append(response)
    return responses


def _normalize_records(
    data: Any,
    input_path: Path,
    response_index: int,
) -> list[dict[str, Any]]:
    """将响应中的 data 字段统一为人员记录列表。"""
    if data is None:
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError(
            f"{input_path} 第 {response_index} 个响应的 data 不是数组或对象"
        )

    records: list[dict[str, Any]] = []
    for data_index, record in enumerate(data):
        if not isinstance(record, dict):
            raise ValueError(
                f"{input_path} 第 {response_index} 个响应的第 {data_index} 条人员记录"
                "不是 JSON 对象"
            )
        records.append(record)
    return records


def collect_persons(input_path: Path) -> tuple[list[dict[str, Any]], int]:
    """读取响应中的人员字段，忽略 total、log_id 等响应包装字段。"""
    responses = _load_responses(input_path)
    rows: list[dict[str, Any]] = []

    for response_index, response in enumerate(responses):
        code = response.get("code")
        if response.get("success") is False or (
            code is not None and code != 200
        ):
            message = response.get("msg") or "未知错误"
            raise ValueError(
                f"{input_path} 第 {response_index} 个响应请求失败: "
                f"code={code!r}, msg={message!r}"
            )

        for record in _normalize_records(
            response.get("data"), input_path, response_index
        ):
            rows.append({field: record.get(field) for field in OUTPUT_FIELDS})

    return rows, len(responses)


def deduplicate_by_person_id(
    rows: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """按学者 ID 去重，保留首次出现的记录和输入顺序。"""
    unique_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    duplicate_count = 0

    for row in rows:
        raw_person_id = row.get("id")
        person_id = str(raw_person_id).strip() if raw_person_id is not None else ""
        if not person_id:
            unique_rows.append(row)
            continue
        if person_id in seen_ids:
            duplicate_count += 1
            continue

        seen_ids.add(person_id)
        unique_rows.append(row)

    return unique_rows, duplicate_count


def _serialize_cell(value: Any) -> str | int | float:
    """将数组编码为 JSON，并将缺失值写为空单元格。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return value
    return str(value)


def write_csv(rows: Sequence[dict[str, Any]], output_path: Path) -> None:
    """以 UTF-8 BOM 原子写入人员字段 CSV。"""
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
            writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        field: _serialize_cell(row.get(field))
                        for field in OUTPUT_FIELDS
                    }
                )

        try:
            temporary_path.replace(output_path)
        except PermissionError:
            # Windows 上目标文件被读取时，回退到直接覆盖。
            shutil.copyfile(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def clean_persons(input_path: Path, output_path: Path) -> tuple[int, int, int]:
    rows, response_count = collect_persons(input_path)
    unique_rows, duplicate_count = deduplicate_by_person_id(rows)
    write_csv(unique_rows, output_path)
    return response_count, len(rows), duplicate_count


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="清洗 AMiner 学者查询 JSON 并生成 CSV",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"输入 JSON 路径（默认: {DEFAULT_INPUT_PATH}）",
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
        response_count, row_count, duplicate_count = clean_persons(
            args.input, args.output
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"清洗失败: {exc}") from exc

    print(
        f"清洗完成: {response_count} 个接口响应，原始学者 {row_count} 条，"
        f"按 id 去重后 {row_count - duplicate_count} 条，"
        f"移除重复 {duplicate_count} 条"
    )
    print(f"CSV 已保存到: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
