"""pytest 固件：接口对象在整个会话内复用同一个连接池，用完统一关闭。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apis.baidu_suggest import BaiduSuggestApi  # noqa: E402
from apis.echo import EchoApi  # noqa: E402


@pytest.fixture(scope="session")
def suggest_api() -> BaiduSuggestApi:
    return BaiduSuggestApi.create()


@pytest.fixture(scope="session")
def echo_api() -> EchoApi:
    return EchoApi.create()
