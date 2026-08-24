"""百度搜索建议接口。

这是一个真实世界里"不规范"的接口：响应是 GBK 编码的 JSONP（键不带引号），
不是标准 JSON。这类协议脏活全部封在本层，用例层只看到干净的业务对象。
"""
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from config import BAIDU_SUGGEST_BASE_URL
from http_client import ApiResponse, HttpClient

logger = logging.getLogger("api.baidu_suggest")

SUGGEST_PATH = "/su"
JSONP_CALLBACK_NAME = "cb"
SUGGEST_TYPE_WEB = 3          # p=3 表示网页搜索建议
FIELD_KEYWORD = "q"
FIELD_SUGGESTIONS = "s"

_OBJECT_START = "{"
_OBJECT_END = "}"
_KEY_VALUE_SEPARATOR = ":"
_FIELD_SEPARATOR = ","


@dataclass(frozen=True)
class SuggestResult:
    """业务视角的返回：用户输入了什么、系统建议了什么。"""

    keyword: str
    suggestions: List[str]


def _skip_whitespace(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def _read_key(body: str, pos: int) -> Tuple[str, int]:
    """从结构位置 pos 处读出键名，返回 (键名, 值的起始位置)。"""
    separator_pos = body.find(_KEY_VALUE_SEPARATOR, pos)
    if separator_pos < 0:
        raise ValueError(f"字段 {body[pos:pos + 20]!r} 缺少 {_KEY_VALUE_SEPARATOR!r}")
    key = body[pos:separator_pos].strip().strip('"')
    return key, _skip_whitespace(body, separator_pos + 1)


def _parse_jsonp_object(body: str) -> Dict[str, Any]:
    """顺序扫描 JSONP 对象体，把所有能解析的字段取出来。

    为什么不用"给裸键补引号再整体 json.loads"：实测空关键词的响应是
    `cb({q:"",p:,s:[]});`，`p` 的值是空的，整体转换必然失败。

    为什么不用"find('s:') 定位字段"：`s:` 会命中字符串值内部——搜索
    `https://x` 时 `q` 的值里就含 `s:`，导致合法响应被判为格式非法。

    这里改为从 `{` 之后顺序推进：只在结构位置上读键名，值一律交给
    JSONDecoder.raw_decode 判定边界，读完一个值再从其结束位置找下一个
    分隔符。位置指针因此永远与结构对齐，字符串值里的 `:`、`,`、`]`
    都不会被误认为结构符号。
    """
    object_start = body.find(_OBJECT_START)
    if object_start < 0:
        raise ValueError(f"响应中找不到 {_OBJECT_START!r}：{body[:200]!r}")

    decoder = json.JSONDecoder()
    fields: Dict[str, Any] = {}
    pos = object_start + 1

    while pos < len(body):
        pos = _skip_whitespace(body, pos)
        if pos >= len(body) or body[pos] == _OBJECT_END:
            break

        key, value_start = _read_key(body, pos)
        try:
            value, pos = decoder.raw_decode(body, value_start)
            fields[key] = value
        except json.JSONDecodeError:
            # 该字段的值不是合法 JSON（真实响应里出现过 `p:` 空值）。
            # 不关心的字段格式再乱也不该影响其他字段，跳过它继续。
            logger.debug("字段 %r 的值无法解析，已跳过", key)
            pos = value_start

        separator_pos = body.find(_FIELD_SEPARATOR, pos)
        if separator_pos < 0:
            break
        pos = separator_pos + 1

    return fields


def parse_suggest(response: ApiResponse) -> SuggestResult:
    """把 JSONP 响应体翻译成 SuggestResult；格式不符即抛错，绝不返回半成品。"""
    body = response.text.strip()
    if not body.startswith(f"{JSONP_CALLBACK_NAME}("):
        raise ValueError(f"响应不是预期的 JSONP 格式：{body[:200]!r}")

    fields = _parse_jsonp_object(body)
    for field in (FIELD_KEYWORD, FIELD_SUGGESTIONS):
        if field not in fields:
            raise ValueError(f"响应中缺少字段 {field!r}，原始响应={body[:200]!r}")

    keyword = fields[FIELD_KEYWORD]
    if not isinstance(keyword, str):
        raise ValueError(f"字段 {FIELD_KEYWORD!r} 不是字符串：{keyword!r}")

    suggestions = fields[FIELD_SUGGESTIONS]
    if not isinstance(suggestions, list):
        raise ValueError(f"字段 {FIELD_SUGGESTIONS!r} 不是数组：{suggestions!r}")
    non_text = [item for item in suggestions if not isinstance(item, str)]
    if non_text:
        raise ValueError(f"字段 {FIELD_SUGGESTIONS!r} 含非字符串元素：{non_text!r}")

    logger.info("解析成功 keyword=%r 建议数=%d", keyword, len(suggestions))
    return SuggestResult(keyword=keyword, suggestions=suggestions)


class BaiduSuggestApi:
    """接口对象：对外暴露业务动作，隐藏 URL、参数名、回调名等细节。"""

    def __init__(self, client: HttpClient):
        self._client = client

    @staticmethod
    def create() -> "BaiduSuggestApi":
        return BaiduSuggestApi(HttpClient(BAIDU_SUGGEST_BASE_URL))

    def search(self, keyword: str) -> ApiResponse:
        """按关键词拉取搜索建议，返回原始响应，便于用例断言状态码与耗时。"""
        return self._client.get(
            SUGGEST_PATH,
            params={"wd": keyword, "p": SUGGEST_TYPE_WEB, "cb": JSONP_CALLBACK_NAME},
        )

    def close(self) -> None:
        self._client.close()
