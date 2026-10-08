#!/usr/bin/env python3
"""将 AMiner 机构详情接口结果合并为结构化 CSV。"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path
from typing import Any, Sequence


AMINER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = AMINER_DIR / "data" / "query_organization_detail"
DEFAULT_OUTPUT_PATH = AMINER_DIR / "data_cleaned" / "organization_detail_cleaned.csv"
INPUT_PATTERN = "*.json"

PROVENANCE_FIELDS = (
    "source_file",
    "response_index",
    "data_index",
    "response_log_id",
    "response_total",
)
COLLECTION_FIELDS = frozenset(("acronyms", "aliases", "details"))
PREFERRED_DETAIL_FIELDS = (
    "id",
    "name",
    "name_en",
    "name_zh",
    "type",
    "acronyms",
    "aliases",
    "details",
    "location",
    "url",
    "image",
)


def _load_responses(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 JSON 文件 {path}: {exc}") from exc

    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError(f"{path} 的顶层结构应为接口响应数组或对象")

    responses: list[dict[str, Any]] = []
    for response_index, response in enumerate(payload):
        if not isinstance(response, dict):
            raise ValueError(f"{path} 第 {response_index} 个响应不是 JSON 对象")
        responses.append(response)
    return responses


def _normalize_data_records(
    data: Any,
    input_path: Path,
    response_index: int,
) -> list[dict[str, Any]]:
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
                f"{input_path} 第 {response_index} 个响应的第 {data_index} 条机构详情"
                "不是 JSON 对象"
            )
        records.append(record)
    return records


def _normalize_collection_fields(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    for field in COLLECTION_FIELDS:
        value = normalized.get(field)
        if value is not None and not isinstance(value, list):
            normalized[field] = [value]
    return normalized


def collect_organization_details(
    input_files: Sequence[Path],
) -> tuple[list[dict[str, Any]], list[str], int]:
    """读取详情响应，返回机构行、CSV 字段和响应数量。"""
    rows: list[dict[str, Any]] = []
    detail_fields: set[str] = set()
    response_count = 0

    for input_path in input_files:
        responses = _load_responses(input_path)
        response_count += len(responses)

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

            records = _normalize_data_records(
                response.get("data"), input_path, response_index
            )
            for data_index, raw_record in enumerate(records):
                record = _normalize_collection_fields(raw_record)
                collisions = set(record).intersection(PROVENANCE_FIELDS)
                if collisions:
                    names = ", ".join(sorted(collisions))
                    raise ValueError(f"机构详情包含保留字段: {names}")

                detail_fields.update(record)
                rows.append(
                    {
                        "source_file": input_path.name,
                        "response_index": response_index,
                        "data_index": data_index,
                        "response_log_id": response.get("log_id"),
                        "response_total": response.get("total"),
                        **record,
                    }
                )

    preferred = [
        field for field in PREFERRED_DETAIL_FIELDS if field in detail_fields
    ]
    extra = sorted(detail_fields.difference(preferred))
    return rows, [*PROVENANCE_FIELDS, *preferred, *extra], response_count


def deduplicate_details_by_id(
    rows: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """按非空机构 ID 去重，保留输入顺序中首次出现的详情。"""
    unique_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    duplicate_count = 0

    for row in rows:
        raw_id = row.get("id")
        organization_id = str(raw_id).strip() if raw_id is not None else ""
        if not organization_id:
            unique_rows.append(row)
            continue
        if organization_id in seen_ids:
            duplicate_count += 1
            continue

        seen_ids.add(organization_id)
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


def write_csv(
    rows: Sequence[dict[str, Any]],
    fieldnames: Sequence[str],
    output: Path,
) -> None:
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


def clean_organization_details(
    data_dir: Path,
    output: Path,
) -> tuple[int, int, int, int]:
    input_files = sorted(data_dir.glob(INPUT_PATTERN), key=lambda path: path.name)
    if not input_files:
        raise FileNotFoundError(f"{data_dir} 中没有匹配 {INPUT_PATTERN} 的文件")

    rows, fieldnames, response_count = collect_organization_details(input_files)
    unique_rows, duplicate_count = deduplicate_details_by_id(rows)
    write_csv(unique_rows, fieldnames, output)
    return len(input_files), response_count, len(rows), duplicate_count


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="合并 AMiner/data/query_organization_detail 下的 JSON 并生成 CSV",
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
        file_count, response_count, row_count, duplicate_count = (
            clean_organization_details(args.data_dir, args.output)
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"清洗失败: {exc}") from exc

    print(
        f"清洗完成: {file_count} 个 JSON 文件，{response_count} 个接口响应，"
        f"原始详情 {row_count} 条，按 ID 去重后 {row_count - duplicate_count} 条，"
        f"移除重复 {duplicate_count} 条"
    )
    print(f"CSV 已保存到: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
