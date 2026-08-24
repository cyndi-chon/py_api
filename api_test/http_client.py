"""HTTP 传输层：只负责"把请求发出去、把结果和耗时带回来"，不理解任何业务。

对外契约是 ApiResponse（纯数据），业务层与用例层都依赖它，
因此替换底层实现（requests -> httpx）不会波及上层。
"""
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import requests
from requests.adapters import HTTPAdapter
from requests.structures import CaseInsensitiveDict
from urllib3.util.retry import Retry

from config import (
    CONNECT_RETRIES,
    CONNECT_TIMEOUT_SECONDS,
    LOG_BODY_MAX_CHARS,
    READ_TIMEOUT_SECONDS,
    RETRY_BACKOFF_FACTOR,
)

logger = logging.getLogger("api.http")


@dataclass(frozen=True)
class ApiResponse:
    """一次调用的完整结果，不可变，便于反复断言。

    elapsed_seconds 是**单次请求往返**耗时，不含连接重试与 backoff 睡眠——
    否则一次重试就会让响应时间断言报"接口变慢"，把排查引向错误方向。
    客户端总耗时（含重试）只进日志，不作为断言依据。
    """

    status_code: int
    text: str
    elapsed_seconds: float
    headers: Mapping[str, str]
    url: str

    def json(self) -> Any:
        """标准 JSON 响应的解析入口；非标准格式由各接口自己解析 text。"""
        return json.loads(self.text)


class HttpClient:
    """带连接复用、超时、连接层重试、结构化日志的客户端。"""

    def __init__(self, base_url: str, default_headers: Optional[Mapping[str, str]] = None):
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        if default_headers:
            self._session.headers.update(default_headers)

        # connect=N 且 read=0/status=0：连接建立失败可重试（请求未发出，幂等性无关），
        # 已经发出的请求一律不重试；raise_on_status=False 保证任何状态码都作为
        # 响应返回给用例，而不是被 urllib3 变成 RetryError 抛掉。
        retry = Retry(
            total=None,
            connect=CONNECT_RETRIES,
            read=0,
            status=0,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            raise_on_status=False,
            allowed_methods=None,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def request(self, method: str, path: str, **kwargs: Any) -> ApiResponse:
        url = f"{self._base_url}/{path.lstrip('/')}"
        started_at = time.perf_counter()
        logger.info("--> %s %s params=%s json=%s",
                    method, url, kwargs.get("params"), kwargs.get("json"))
        try:
            raw = self._session.request(
                method,
                url,
                timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                **kwargs,
            )
        except requests.RequestException as exc:
            # 不静默吞错：补足定位所需的上下文后向上抛，由用例判定失败
            total_seconds = time.perf_counter() - started_at
            logger.error("<-- %s %s FAILED after %.3fs: %s", method, url, total_seconds, exc)
            raise

        total_seconds = time.perf_counter() - started_at
        request_seconds = raw.elapsed.total_seconds()
        body_preview = raw.text[:LOG_BODY_MAX_CHARS]
        logger.info("<-- %s %s %s 单次=%.3fs 总计=%.3fs body=%s",
                    method, url, raw.status_code, request_seconds, total_seconds, body_preview)

        return ApiResponse(
            status_code=raw.status_code,
            text=raw.text,
            elapsed_seconds=request_seconds,
            headers=CaseInsensitiveDict(raw.headers),
            url=raw.url,
        )

    def get(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> ApiResponse:
        return self.request("POST", path, **kwargs)

    def close(self) -> None:
        self._session.close()
