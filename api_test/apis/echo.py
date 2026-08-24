"""Postman Echo 回显接口：把请求原样回显，适合验证参数、请求头、方法是否正确送达。"""
import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from config import ECHO_BASE_URL
from http_client import ApiResponse, HttpClient

GET_PATH = "/get"
POST_PATH = "/post"
STATUS_PATH = "/status/{code}"

FIELD_QUERY_PARAMS = "args"
FIELD_HEADERS = "headers"
FIELD_JSON_BODY = "json"
HEADER_CONTENT_TYPE = "content-type"


@dataclass(frozen=True)
class EchoResult:
    """回显结果的业务视图：服务端实际收到的查询参数、JSON 体、Content-Type。"""

    query_params: Dict[str, Any]
    json_body: Optional[Any]
    content_type: Optional[str]


def parse_echo(response: ApiResponse) -> EchoResult:
    """解析回显体；不是合法 JSON 时带上 url 和响应片段抛错，便于定位。

    注意服务端对 JSON POST 会同时返回 `data` 和 `json` 两份同样的内容，
    这里固定只读 `json`（已解析的请求体），不做 fallback——同一事实只认一个来源。
    """
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"回显响应不是合法 JSON：url={response.url} 响应={response.text[:200]!r}"
        ) from exc

    echoed_headers = payload.get(FIELD_HEADERS, {})
    return EchoResult(
        query_params=payload.get(FIELD_QUERY_PARAMS, {}),
        json_body=payload.get(FIELD_JSON_BODY),
        content_type=echoed_headers.get(HEADER_CONTENT_TYPE),
    )


class EchoApi:
    def __init__(self, client: HttpClient):
        self._client = client

    @staticmethod
    def create() -> "EchoApi":
        return EchoApi(HttpClient(ECHO_BASE_URL))

    def echo_get(self, params: Mapping[str, Any]) -> ApiResponse:
        return self._client.get(GET_PATH, params=params)

    def echo_post(self, body: Mapping[str, Any]) -> ApiResponse:
        return self._client.post(POST_PATH, json=body)

    def expect_status(self, code: int) -> ApiResponse:
        """让服务端返回指定状态码，用于验证客户端对错误码的处理。"""
        return self._client.get(STATUS_PATH.format(code=code))

    def close(self) -> None:
        self._client.close()
