"""通用断言：把"每个接口都要查的东西"抽成一处，用例里不再重复写。"""
from typing import Iterable

from config import HTTP_OK, RESPONSE_TIME_SLA_SECONDS
from http_client import ApiResponse


def assert_status(response: ApiResponse, expected: int = HTTP_OK) -> None:
    assert response.status_code == expected, (
        f"状态码不符：期望 {expected}，实际 {response.status_code}，url={response.url}"
    )


def assert_within_sla(response: ApiResponse, sla_seconds: float = RESPONSE_TIME_SLA_SECONDS) -> None:
    assert response.elapsed_seconds <= sla_seconds, (
        f"响应超时：耗时 {response.elapsed_seconds:.3f}s > SLA {sla_seconds}s，url={response.url}"
    )


def assert_response_ok(
    response: ApiResponse,
    expected_status: int = HTTP_OK,
    sla_seconds: float = RESPONSE_TIME_SLA_SECONDS,
) -> None:
    """一次调用的基线检查：状态码符合预期 + 在 SLA 内返回。

    expected_status 是"这个用例期望的状态码"，可以是 404/500——
    对错误码用例来说，拿到该错误码就是通过。
    """
    assert_status(response, expected_status)
    assert_within_sla(response, sla_seconds)


def assert_keys_present(payload: dict, keys: Iterable[str]) -> None:
    missing = [key for key in keys if key not in payload]
    assert not missing, f"响应缺少字段 {missing}，实际字段 {sorted(payload)}"
