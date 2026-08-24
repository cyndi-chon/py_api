# 接口自动化脚本（公开接口示例）

没有接口文档时，用两个公开接口作为被测对象跑通一套完整的接口自动化流程。

## 被测接口

| 接口 | 地址 | 为什么选它 |
|---|---|---|
| 百度搜索建议 | `https://suggestion.baidu.com/su` | 真实的"不规范"接口：GBK 编码 + JSONP（键不带引号），适合练手协议解析 |
| Postman Echo | `https://postman-echo.com` | 请求原样回显，可精确校验参数、请求体、请求头是否正确送达；还能指定返回任意状态码 |

两者都无需 API Key。

## 目录结构

```
api_test/
├── config.py                    # 所有可调参数（地址、超时、重试、SLA）集中一处
├── http_client.py               # 传输层：超时/重试/连接复用/结构化日志 → ApiResponse
├── checks.py                    # 通用断言：状态码、响应时间 SLA、字段存在性
├── apis/
│   ├── baidu_suggest.py         # 接口对象：屏蔽 JSONP/GBK 细节，产出 SuggestResult
│   └── echo.py                  # 接口对象：GET/POST 回显、指定状态码
├── tests/
│   ├── conftest.py              # 会话级 fixture，全套用例复用同一连接池
│   ├── test_baidu_suggest.py
│   └── test_echo.py
└── pytest.ini                   # 用例发现规则、标记、日志格式
```

分层的意义：**协议细节只存在于 `apis/`，用例里看不到 URL、参数名、JSONP 回调名。** 接口改了只改一处，用例不动。

## 运行

```bash
cd api_test
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python -m pytest                    # 全部用例
.venv/bin/python -m pytest -m smoke           # 只跑冒烟
.venv/bin/python -m pytest -m negative        # 只跑异常/边界
.venv/bin/python -m pytest --html=report.html --self-contained-html   # 生成 HTML 报告
```

切换环境地址不用改代码，用环境变量覆盖：

```bash
BAIDU_SUGGEST_BASE_URL=https://staging.example.com .venv/bin/python -m pytest
```

> 注意：如果直接用全局 `python3 -m pytest`，本机全局环境里有个损坏的 pytest 插件
> （web3 的 `pytest_ethereum` 与 `eth_typing` 版本不兼容）会导致 pytest 启动失败。
> 用上面的虚拟环境即可，或临时加 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`。

## 当前结果

9 passed —— 3 个搜索建议正向（参数化）、3 个边界（空/超长/特殊字符关键词）、3 个回显（GET 参数、POST body、404）。

## 跑这套脚本时真实踩到的三个坑

这几点是实际调通过程中接口暴露出来的，不是设想的：

1. **空关键词时响应体是 `cb({q:"",p:,s:[]});`** —— `p` 的值是空的，整体并非合法 JSON。
   所以解析器没有采用"给裸键补引号再整体 `json.loads`"的做法（那样会直接崩），
   而是用 `JSONDecoder().raw_decode()` **只取需要的 `q` 和 `s` 两个字段**，
   让 JSON 解析器自己判定值的边界。不关心的字段格式再乱也不影响。

2. **建议词大小写不固定** —— 搜 `pytest` 会返回 `Pytest干什么用的`。
   相关性断言必须忽略大小写，否则偶发失败。第一次跑就是这条挂的。

3. **超长关键词（200 字符）返回 `q:""` 且建议为空** —— 服务端静默降级而不是报错。
   所以边界用例只断言"响应结构合法"，不断言"建议词非空"。

## 扩展到真实项目

- **加接口**：在 `apis/` 下新增一个接口对象类，不改任何现有代码
- **加环境**：`config.py` 里已用 `os.getenv`，接 CI 时注入环境变量即可
- **加鉴权**：在 `HttpClient` 构造时传 `default_headers`，或在接口对象里注入 token
- **数据驱动**：`@pytest.mark.parametrize` 的数据源换成读 YAML/CSV/Excel
- **接 CI**：`pytest --html=report.html` 产出报告，退出码非 0 即失败，可直接卡流水线
