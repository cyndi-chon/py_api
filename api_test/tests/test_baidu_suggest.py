"""百度搜索建议接口用例。"""
import pytest

from apis.baidu_suggest import parse_suggest
from checks import assert_healthy

SEARCH_KEYWORDS = ["python", "自动化测试", "pytest"]
LONG_KEYWORD = "a" * 200
SPECIAL_KEYWORD = "!@#$%^&*()"


@pytest.mark.smoke
@pytest.mark.parametrize("keyword", SEARCH_KEYWORDS)
def test_建议词非空且与关键词相关(suggest_api, keyword):
    response = suggest_api.search(keyword)
    assert_healthy(response)

    result = parse_suggest(response)
    assert result.keyword == keyword, f"回显关键词不符：{result.keyword!r} != {keyword!r}"
    assert result.suggestions, f"关键词 {keyword!r} 没有返回任何建议词"
    # 百度会返回首字母大写的建议词（如 "Pytest干什么用的"），相关性判断需忽略大小写
    irrelevant = [item for item in result.suggestions if keyword.lower() not in item.lower()]
    assert not irrelevant, f"存在与关键词无关的建议词：{irrelevant}"


@pytest.mark.negative
def test_空关键词时接口仍正常返回且建议为空(suggest_api):
    response = suggest_api.search("")
    assert_healthy(response)

    result = parse_suggest(response)
    assert result.keyword == ""
    assert result.suggestions == [], f"空关键词却返回了建议词：{result.suggestions}"


@pytest.mark.negative
@pytest.mark.parametrize(
    "keyword, case_name",
    [(LONG_KEYWORD, "超长关键词"), (SPECIAL_KEYWORD, "特殊字符关键词")],
)
def test_异常关键词不应导致服务端报错(suggest_api, keyword, case_name):
    response = suggest_api.search(keyword)
    assert_healthy(response)
    # 建议词可以为空，但响应必须是可解析的合法结构
    parse_suggest(response)
