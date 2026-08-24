"""全局配置：所有可调参数集中在此，代码里不出现字面量。"""
import os
from http import HTTPStatus

# ---- 被测服务地址 ----
BAIDU_SUGGEST_BASE_URL = os.getenv("BAIDU_SUGGEST_BASE_URL", "https://suggestion.baidu.com")
ECHO_BASE_URL = os.getenv("ECHO_BASE_URL", "https://postman-echo.com")

# ---- 传输层参数 ----
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 10.0
# 只重试"连接尚未建立"的失败——此时请求还没发出去，重试对任何方法都安全。
# HTTP 状态码一律如实返回：5xx 是被测系统的缺陷，测试工具的职责是上报而不是掩盖。
CONNECT_RETRIES = 2
RETRY_BACKOFF_FACTOR = 0.5

# ---- 断言基线 ----
HTTP_OK = HTTPStatus.OK
HTTP_NOT_FOUND = HTTPStatus.NOT_FOUND
HTTP_INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR
RESPONSE_TIME_SLA_SECONDS = 5.0   # 单次请求往返上限（含首次 TLS 握手开销）

# ---- 日志 ----
LOG_BODY_MAX_CHARS = 300          # 日志里响应体最多打印多少字符，避免刷屏
