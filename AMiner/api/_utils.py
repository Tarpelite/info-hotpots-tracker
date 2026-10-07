import json
from collections.abc import Sequence
from typing import Any

from .aminer_client import AMinerClient


def client_or_default(client: AMinerClient | None = None) -> AMinerClient:
    return client if client is not None else AMinerClient.from_default_config()


def compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"缺少必填参数 {name}：请传入非空字符串")
    return value.strip()


def optional_text(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return require_text(value, name)


def require_text_list(values: Any, name: str, max_items: int | None = None) -> list[str]:
    if isinstance(values, str) or not isinstance(values, Sequence) or not values:
        raise ValueError(f"缺少必填参数 {name}：请传入非空字符串数组")

    normalized = [require_text(value, name) for value in values]
    if max_items is not None and len(normalized) > max_items:
        raise ValueError(f"参数 {name} 数量不能超过 {max_items} 个")

    return normalized


def optional_int(
    value: Any,
    name: str,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int | None:
    if value is None:
        return None
    return require_int(value, name, min_value=min_value, max_value=max_value)


def require_int(
    value: Any,
    name: str,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"参数 {name} 必须是整数")
    if min_value is not None and value < min_value:
        raise ValueError(f"参数 {name} 不能小于 {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"参数 {name} 不能大于 {max_value}")
    return value


def optional_bool(value: Any, name: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"参数 {name} 必须是布尔值")
    return value


def json_array_string(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return require_text(value, name)
    return json.dumps(value, ensure_ascii=False)


def require_one_present(values: dict[str, Any], names: Sequence[str], message: str) -> None:
    if not any(values.get(name) is not None for name in names):
        raise ValueError(message)


def require_exactly_one_present(values: dict[str, Any], names: Sequence[str], message: str) -> None:
    present_count = sum(values.get(name) is not None for name in names)
    if present_count != 1:
        raise ValueError(message)
