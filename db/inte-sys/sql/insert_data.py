#!/usr/bin/env python3
"""Convert the cleaned AMiner CSV files into Cloudflare D1 INSERT SQL."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from collections.abc import Iterator, Sequence
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "AMiner" / "data_cleaned"
DEFAULT_SCHEMA = SCRIPT_DIR / "schema.sql"
DEFAULT_OUTPUT = SCRIPT_DIR / "insert_data.sql"

# Insert parent records before the junction records so foreign keys remain valid.
TABLE_SOURCES = (
    ("paper", "paper_detail_cleaned.csv"),
    ("organization", "organization_detail_cleaned.csv"),
    ("paper_author", "paper_author_cleaned.csv"),
)


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return number


def quote_identifier(value: str) -> str:
    return f'"{value.replace(chr(34), chr(34) * 2)}"'


def sql_literal(value: str | None, declared_type: str, context: str) -> str:
    if value is None or value == "":
        return "NULL"
    if "\x00" in value:
        raise ValueError(f"NUL byte is not supported in {context}")

    affinity = declared_type.upper().split("(", 1)[0].strip()
    if affinity == "INTEGER":
        try:
            return str(int(value))
        except ValueError as exc:
            raise ValueError(f"expected an integer in {context}, got {value!r}") from exc

    return "'" + value.replace("'", "''") + "'"


def read_schema(schema_path: Path) -> sqlite3.Connection:
    if not schema_path.is_file():
        raise FileNotFoundError(f"schema file not found: {schema_path}")

    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(schema_path.read_text(encoding="utf-8-sig"))
    except sqlite3.Error:
        connection.close()
        raise
    return connection


def table_columns(
    connection: sqlite3.Connection, table_name: str
) -> list[tuple[str, str]]:
    rows = connection.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()
    if not rows:
        raise ValueError(f"table {table_name!r} is missing from the schema")
    return [(row[1], row[2]) for row in rows]


def insert_statements(
    table_name: str,
    columns: Sequence[tuple[str, str]],
    rows: Iterator[dict[str, str]],
    batch_size: int,
    max_statement_bytes: int,
) -> Iterator[tuple[str, int]]:
    column_sql = ", ".join(quote_identifier(name) for name, _ in columns)
    prefix = f"INSERT INTO {quote_identifier(table_name)} ({column_sql}) VALUES\n"
    batch: list[str] = []

    for row_number, row in enumerate(rows, start=2):
        values = ", ".join(
            sql_literal(
                row.get(name),
                declared_type,
                f"{table_name}.{name} at CSV row {row_number}",
            )
            for name, declared_type in columns
        )
        row_sql = f"({values})"
        candidate = prefix + ",\n".join((*batch, row_sql)) + ";\n"

        if batch and (
            len(batch) >= batch_size
            or len(candidate.encode("utf-8")) > max_statement_bytes
        ):
            yield prefix + ",\n".join(batch) + ";\n", len(batch)
            batch = []
            candidate = prefix + row_sql + ";\n"

        if len(candidate.encode("utf-8")) > max_statement_bytes:
            raise ValueError(
                f"one {table_name} row exceeds the statement byte limit "
                f"({max_statement_bytes}) at CSV row {row_number}"
            )
        batch.append(row_sql)

    if batch:
        yield prefix + ",\n".join(batch) + ";\n", len(batch)


def write_table(
    output,
    connection: sqlite3.Connection,
    table_name: str,
    csv_path: Path,
    batch_size: int,
    max_statement_bytes: int,
) -> tuple[int, int]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    columns = table_columns(connection, table_name)
    required_names = [name for name, _ in columns]
    row_count = 0
    statement_count = 0

    output.write(f"-- Source: {csv_path.name}\n")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header: {csv_path}")

        missing = [name for name in required_names if name not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"{csv_path.name} is missing schema columns: {', '.join(missing)}"
            )

        for statement, rows_in_statement in insert_statements(
            table_name,
            columns,
            reader,
            batch_size,
            max_statement_bytes,
        ):
            output.write(statement)
            output.write("\n")
            row_count += rows_in_statement
            statement_count += 1

    return row_count, statement_count


def generate_sql(
    data_dir: Path,
    schema_path: Path,
    output_path: Path,
    batch_size: int,
    max_statement_bytes: int,
) -> list[tuple[str, int, int]]:
    connection = read_schema(schema_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(output_path.name + ".tmp")
    results: list[tuple[str, int, int]] = []

    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as output:
            output.write("-- Generated by db/insert_data.py. Do not edit manually.\n")
            output.write("-- Apply db/schema.sql before executing this file.\n\n")

            for table_name, csv_name in TABLE_SOURCES:
                row_count, statement_count = write_table(
                    output,
                    connection,
                    table_name,
                    data_dir / csv_name,
                    batch_size,
                    max_statement_bytes,
                )
                results.append((table_name, row_count, statement_count))

        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert cleaned AMiner CSV files into batched D1 INSERT SQL."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=positive_int, default=100)
    parser.add_argument(
        "--max-statement-bytes",
        type=positive_int,
        default=90_000,
        help="maximum UTF-8 size of each INSERT statement (default: 90000)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = generate_sql(
        args.data_dir.resolve(),
        args.schema.resolve(),
        args.output.resolve(),
        args.batch_size,
        args.max_statement_bytes,
    )

    total_rows = 0
    total_statements = 0
    for table_name, row_count, statement_count in results:
        total_rows += row_count
        total_statements += statement_count
        print(f"{table_name}: {row_count} rows, {statement_count} statements")
    print(f"Wrote {total_rows} rows in {total_statements} statements to {args.output.resolve()}")


if __name__ == "__main__":
    main()
