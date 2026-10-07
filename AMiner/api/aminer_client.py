import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "aminer_credentials.json"
JSON_CONTENT_TYPE = "application/json;charset=utf-8"


class AMinerAPIError(RuntimeError):
    """Raised when an AMiner API request fails."""


class AMinerClient:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.base_url = str(config.get("base_url", "")).strip()
        self.timeout = float(config.get("timeout_seconds", 15))

    @classmethod
    def from_default_config(cls) -> "AMinerClient":
        return cls.from_config_file(DEFAULT_CONFIG_PATH)

    @classmethod
    def from_config_file(cls, config_path: str | Path) -> "AMinerClient":
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)

        return cls(config)

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return self.request("POST", endpoint, params=params, json_body=payload if payload is not None else {})

    def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        method = method.upper()
        url = self._build_url(endpoint, params)
        headers = self._build_headers(content_type=JSON_CONTENT_TYPE if method == "POST" else None)
        data = None

        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")

        request = Request(url, data=data, headers=headers, method=method)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return self._decode_response(body)
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise AMinerAPIError(f"{method} {url} -> HTTP {exc.code}: {error_body}") from exc
        except URLError as exc:
            raise AMinerAPIError(f"网络请求失败: {exc.reason}") from exc

    def _build_url(self, endpoint: str, params: dict[str, Any] | None) -> str:
        if self._is_absolute_url(endpoint):
            url = endpoint
        else:
            if not self.base_url:
                raise ValueError("请先在配置文件中填写 base_url")
            base_url = self.base_url.rstrip("/")
            endpoint_path = endpoint.lstrip("/")
            if base_url.endswith("/api") and endpoint_path.startswith("api/"):
                endpoint_path = endpoint_path[len("api/") :]
            url = urljoin(base_url + "/", endpoint_path)

        query_params = self._normalize_query_params(params)
        if query_params:
            connector = "&" if "?" in url else "?"
            url = f"{url}{connector}{urlencode(query_params)}"

        return url

    @staticmethod
    def _normalize_query_params(params: dict[str, Any] | None) -> dict[str, Any]:
        if not params:
            return {}

        query_params = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (list, dict)):
                query_params[key] = json.dumps(value, ensure_ascii=False)
            else:
                query_params[key] = value

        return query_params

    def _build_headers(self, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Intelligence-System-AMiner-Client/1.0",
        }

        if content_type:
            headers["Content-Type"] = content_type

        api_key = str(self.config.get("api_key", "")).strip()
        api_key_header = str(self.config.get("api_key_header", "X-API-Key")).strip()
        if api_key and api_key_header:
            headers[api_key_header] = api_key

        token = str(self.config.get("token", "")).strip()
        if not token:
            token = os.getenv("AMINER_API_KEY", "").strip()
        token_header = str(self.config.get("token_header", "Authorization")).strip()
        token_prefix = str(self.config.get("token_prefix", ""))
        if token and token_header:
            headers[token_header] = f"{token_prefix}{token}" if token_prefix else token

        platform = str(self.config.get("platform", "")).strip()
        if platform:
            headers["X-Platform"] = platform

        extra_headers = self.config.get("extra_headers", {})
        if isinstance(extra_headers, dict):
            headers.update({str(key): str(value) for key, value in extra_headers.items()})

        return headers

    @staticmethod
    def _decode_response(body: str) -> Any:
        if not body:
            return None

        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body

    @staticmethod
    def _is_absolute_url(url: str) -> bool:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
