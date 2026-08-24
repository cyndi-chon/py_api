"""回显接口用例：验证请求参数、请求体、错误状态码的处理。"""
import pytest

from apis.echo import parse_echo
from checks import assert_healthy, assert_keys_present
from config import HTTP_NOT_FOUND

QUERY_PARAMS = {"env": "staging", "page": "1"}
POST_BODY = {"username": "tester", "roles": ["qa", "dev"], "active": True}


@pytest.mark.smoke
def test_GET请求的查询参数被完整送达(echo_api):
    response = echo_api.echo_get(QUERY_PARAMS)
    assert_healthy(response)

    result = parse_echo(response)
    assert result.query_params == QUERY_PARAMS, (
        f"参数被篡改：发送 {QUERY_PARAMS}，回显 {result.query_params}"
    )


@pytest.mark.smoke
def test_POST请求的JSON体被完整送达(echo_api):
    response = echo_api.echo_post(POST_BODY)
    assert_healthy(response)

    payload = response.json()
    assert_keys_present(payload, ["json", "headers", "url"])
    assert payload["json"] == POST_BODY, (
        f"请求体被篡改：发送 {POST_BODY}，回显 {payload['json']}"
    )
    assert payload["headers"]["content-type"].startswith("application/json")


@pytest.mark.negative
def test_服务端返回404时客户端如实上报(echo_api):
    response = echo_api.expect_status(HTTP_NOT_FOUND)
    # 404 是本用例的预期结果，不是失败
    assert_healthy(response, expected_status=HTTP_NOT_FOUND)
