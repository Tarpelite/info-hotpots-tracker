import argparse
import json
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__:
    from .batch.api_integrated import paper as paper_api
else:  # 支持直接执行 `python AMiner/main.py`
    import batch.api_integrated.paper as paper_api

DATA_DIR = Path(__file__).resolve().parent / "data"

# 只暴露已实现的接口，避免通过输入参数调用任意对象。
FUNCTIONS: dict[str, Callable[..., Any]] = {
    "query_paper_lists": paper_api.query_paper_lists,
    "query_paper_detail": paper_api.query_paper_detail,
}


def _build_output_path(function_name: str, filename: str | Path) -> Path:
    """生成 ``AMiner/data/<调用函数名>/<文件名>.json`` 路径。"""
    function_dir = Path(function_name)
    if function_dir.name != function_name or function_name in {"", ".", ".."}:
        raise ValueError("function_name 必须是合法的单层目录名")

    relative_path = Path(filename)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("filename 必须是函数数据目录下的相对路径")
    if relative_path.name in {"", "."}:
        raise ValueError("filename 不能为空")
    if relative_path.suffix.lower() != ".json":
        relative_path = relative_path.with_suffix(".json")

    return DATA_DIR / function_dir / relative_path


def save_data_to_json(
    data: Any,
    function_name: str,
    filename: str | Path = "aminer_data.json",
) -> Path:
    """JSON 序列化抓取结果，并保存到调用函数对应的数据目录。"""
    output_path = _build_output_path(function_name, filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return output_path


def main(
    function_name: str | None = None,
    parameters: Mapping[str, Any] | None = None,
    output_filename: str | Path | None = None,
    **kwargs: Any,
) -> Any:
    """根据函数名调用对应抓取函数，并把返回结果保存为 JSON。

    ``parameters`` 适合传入字典；``kwargs`` 便于 Python 代码直接以关键字
    参数调用。两者同时提供时，``kwargs`` 优先。
    """
    if function_name is None:
        raise ValueError("--function 必须指定")
    function = FUNCTIONS.get(function_name)
    if function is None:
        available = ", ".join(sorted(FUNCTIONS))
        raise ValueError(f"不支持的函数 {function_name!r}，可选函数：{available}")

    call_parameters = dict(parameters or {})
    call_parameters.update(kwargs)
    result = function(**call_parameters)
    if output_filename is None:
        output_filename = f"{_build_default_filename(function_name, call_parameters)}.json"

    save_data_to_json(result, function_name, output_filename)
    return result


def _json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            f"--params 不是合法的 JSON: {exc.msg}"
        ) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--params 必须是 JSON 对象")
    return parsed


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="调用 AMiner 数据接口，并将抓取结果保存到 AMiner/data",
    )
    parser.add_argument(
        "function",
        nargs="?",
        choices=sorted(FUNCTIONS),
        help="要调用的函数（也可使用 --function 指定）",
    )
    parser.add_argument(
        "--function",
        dest="function_option",
        choices=sorted(FUNCTIONS),
        help=f"要调用的函数",
    )
    parser.add_argument(
        "--params",
        type=_json_object,
        default={},
        metavar="JSON",
        help='函数参数，例如 \"{\"keywords\": [\"生命科学\"]}\"',
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="函数数据目录下的输出文件名（默认为 <函数名>_<参数>.json）",
    )
    parser.add_argument(
        "--list-functions",
        action="store_true",
        help="列出所有可调用函数后退出",
    )
    return parser.parse_args(argv)


def _build_default_filename(function_name: str, params: dict) -> str:
    """根据函数名和参数拼接生成默认文件名（不含扩展名）。"""
    if not params:
        return function_name

    # 将参数按键名排序后序列化，保证结果稳定可复现
    param_str = json.dumps(
        params, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )

    # 替换掉文件名中不允许出现的字符（Windows/Linux 通用）
    param_str = re.sub(r'[\\/:*?"<>|\s]+', "_", param_str)

    # 控制文件名长度，避免超过系统限制
    max_len = 150
    if len(function_name) + 1 + len(param_str) > max_len:
        param_str = param_str[: max_len - len(function_name) - 1]

    return f"{function_name}_{param_str}"


def cli(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.list_functions:
        print("\n".join(sorted(FUNCTIONS)))
        return 0

    function_name = args.function_option or args.function
    if args.function and args.function_option and args.function != args.function_option:
        raise SystemExit("位置参数 function 与 --function 指定的函数不一致")

    try:
        main(function_name, args.params, args.output)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"参数错误: {exc}") from exc

    output_filename = args.output
    if output_filename is None:
        default_name = _build_default_filename(function_name, args.params)
        output_filename = f"{default_name}.json"
    output_path = _build_output_path(function_name, output_filename)
    print(f"抓取完成，结果已保存到: {output_path}")


if __name__ == "__main__":
    raise SystemExit(cli())
