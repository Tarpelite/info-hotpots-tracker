#!/usr/bin/env python3
"""清洗 AMiner 机构查询结果，仅保留机构别名、ID 和名称。"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Sequence


AMINER_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = AMINER_DIR / "data" / "query_organizations"
DEFAULT_OUTPUT_PATH = AMINER_DIR / "data_cleaned" / "organization_cleaned.csv"
INPUT_PATTERN = "*.json"
OUTPUT_FIELDS = ("aliases", "org_id", "org_name")


def _load_responses(path: Path) -> list[dict[str, Any]]:
    """读取单个 JSON 文件，并统一为接口响应列表。"""
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


def _normalize_records(
    data: Any,
    input_path: Path,
    response_index: int,
) -> list[dict[str, Any]]:
    """将响应中的 data 字段统一为机构记录列表。"""
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
                f"{input_path} 第 {response_index} 个响应的第 {data_index} 条机构"
                "不是 JSON 对象"
            )
        records.append(record)
    return records


def collect_organizations(
    input_files: Sequence[Path],
) -> tuple[list[dict[str, Any]], int]:
    """读取所有响应并仅保留 aliases、org_id、org_name。"""
    rows: list[dict[str, Any]] = []
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

            for record in _normalize_records(
                response.get("data"), input_path, response_index
            ):
                rows.append({field: record.get(field) for field in OUTPUT_FIELDS})

    return rows, response_count


def deduplicate_by_org_id(
    rows: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """按非空 org_id 去重，保留输入顺序中首次出现的记录。"""
    unique_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    duplicate_count = 0

    for row in rows:
        raw_org_id = row.get("org_id")
        org_id = str(raw_org_id).strip() if raw_org_id is not None else ""
        if not org_id:
            unique_rows.append(row)
            continue
        if org_id in seen_ids:
            duplicate_count += 1
            continue

        seen_ids.add(org_id)
        unique_rows.append(row)

    return unique_rows, duplicate_count


def _serialize_cell(value: Any) -> str | int | float:
    """将集合编码为 JSON，缺失值编码为空单元格。"""
    if value is None:
        return ""
    if isinstance(value, (list, dict, bool)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, (str, int, float)):
        return value
    return str(value)


def write_csv(rows: Sequence[dict[str, Any]], output_path: Path) -> None:
    """以 UTF-8 BOM 写入 CSV，兼容 Excel 直接打开中文。"""
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
            shutil.copyfile(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def clean_organizations(
    data_dir: Path, output_path: Path
) -> tuple[int, int, int, int]:
    input_files = sorted(data_dir.glob(INPUT_PATTERN), key=lambda path: path.name)
    if not input_files:
        raise FileNotFoundError(f"{data_dir} 中没有匹配 {INPUT_PATTERN} 的文件")

    rows, response_count = collect_organizations(input_files)
    unique_rows, duplicate_count = deduplicate_by_org_id(rows)
    write_csv(unique_rows, output_path)
    return len(input_files), response_count, len(rows), duplicate_count


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="清洗 AMiner/data/query_organizations 下的 JSON 并生成 CSV",
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
            clean_organizations(args.data_dir, args.output)
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"清洗失败: {exc}") from exc

    print(
        f"清洗完成: {file_count} 个 JSON 文件，{response_count} 个接口响应，"
        f"原始机构 {row_count} 条，按 org_id 去重后 "
        f"{row_count - duplicate_count} 条，移除重复 {duplicate_count} 条"
    )
    print(f"CSV 已保存到: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
