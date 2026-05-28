# AgentEval 项目指导书

## 一、项目概述

**AgentEval** 是一个面向 AI Agent 产品的轻量级自动化评测框架。它的核心思路是：

> 用 JSON 定义测试用例 → 批量调用 LLM → 基于规则自动评分 → 输出 CSV + HTML 报告

目标是展示 AI Agent 质量保障领域的关键能力：测试用例设计、自动化执行、评分策略、报告生成和问题归因。整个项目不依赖 Web 框架或数据库，**一行命令即可运行**。

---

## 二、功能清单

| 功能 | 说明 |
|---|---|
| JSON 用例管理 | 用结构化 JSON 定义测试用例，覆盖 7 大测试维度 |
| 双模式 LLM 调用 | mock 模式（离线可用）+ api 模式（支持 DeepSeek / OpenAI 兼容 API） |
| 批量执行引擎 | 自动遍历用例，调用 LLM，记录回答、耗时、状态和错误信息 |
| 规则评分 | 关键词命中、JSON 格式校验、长度约束、安全拒答检测 |
| CSV 结果输出 | 每条 case 的详细得分、回答内容、失败原因 |
| HTML 可视化报告 | 通过率卡片、分类统计饼表、详细结果表格、失败原因汇总 |
| 终端概要输出 | 运行完成后即时展示概况，无需打开文件 |
| 命令行参数 | `--mock` / `--api` / `--case-file` 灵活切换运行方式 |
| 环境变量管理 | API Key 通过 `.env` 文件管理，不硬编码，安全可配置 |

---

## 三、项目结构与各文件职责

```
├── run_eval.py                  # 【主入口】串联全流程的调度器
├── src/
│   ├── agent_client.py          # 【LLM 客户端】mock + api 双模式封装
│   ├── case_loader.py           # 【用例加载器】读取并校验 cases.json
│   ├── evaluator.py             # 【评测引擎】批量执行用例，收集原始结果
│   ├── scorer.py                # 【评分模块】基于规则打分，判定通过/失败
│   └── reporter.py              # 【报告生成器】输出 CSV 和 HTML 报告
├── cases/
│   └── cases.json               # 【测试用例集】36 条，7 个类别
├── reports/                     # 【输出目录】自动生成的结果文件
├── .env.example                 # 【配置模板】环境变量示例
├── requirements.txt             # 【依赖清单】仅 requests + python-dotenv
└── README.md                    # 【项目说明】
```

### 3.1 run_eval.py — 主调度器

**职责**：解析命令行参数，按顺序调用各模块完成一次完整评测。

**核心流程**：
```
load_cases() → AgentClient() → Evaluator.run() → scorer.score_result() → generate_reports()
```

**关键设计**：
- 通过 `argparse` 支持 `--mock`、`--api`、`--case-file` 三种参数
- 如果 API 模式但未配置 Key，自动降级为 mock 模式并给出警告
- 终端输出按类别分组统计，方便一眼看出薄弱环节

### 3.2 agent_client.py — LLM 客户端

**职责**：封装大模型调用，对上层屏蔽 mock 和真实 API 的差异。

**双模式设计**：

| 模式 | 触发条件 | 行为 |
|---|---|---|
| mock | `USE_MOCK=true` 或 `--mock` | 预设规则返回模拟回答，模拟 50-300ms 延迟 |
| api | `USE_MOCK=false` 且配置了 Key | 调用 DeepSeek / OpenAI 兼容的 `/v1/chat/completions` |

**mock 模式的智能逻辑**：
- 检测 prompt 中是否包含 "JSON" → 返回 JSON 格式的模拟回答
- 检测 prompt 中是否包含敏感词（违法、攻击、恶意等）→ 返回拒绝回答
- 默认 → 从预设词库中随机抽取，模拟不同场景

**异常处理**：
- 超时：捕获 `requests.exceptions.Timeout`，标记 `reason=timeout`
- 连接错误：捕获 `ConnectionError`，标记 `reason=connection_error`
- HTTP 错误：非 200 状态码记录响应体前 200 字符
- 未知异常：兜底捕获，标记 `reason=unknown_error`

### 3.3 case_loader.py — 用例加载器

**职责**：从 JSON 文件读取测试用例，校验格式合法性。

**校验规则**：
- 必填字段：`case_id`、`category`
- `category` 必须在 7 个合法类别之内
- 至少包含 `prompt` 或 `messages` 之一
- 校验失败抛出 `CaseLoadError` 并指明具体问题

### 3.4 evaluator.py — 评测引擎

**职责**：遍历用例，调用 `AgentClient`，收集每条 case 的原始结果。

**多轮对话处理**：
- 单轮 case：直接用 `prompt` 调用
- 多轮 case：将 `messages` 数组传给 client，同时从 messages 拼接出 display_prompt 用于报告展示
- 这种设计使得多轮对话的实现不影响评分和报告模块——它们只看到统一的 `prompt` 字段

### 3.5 scorer.py — 评分模块

**职责**：根据规则对每条结果打分，判定通过/失败，给出失败原因。

**评分维度与逻辑**：

| 维度 | 触发条件 | 扣分规则 |
|---|---|---|
| API 失败 | `success=False` | **直接 0 分**，reason 标记具体错误类型 |
| 空回答 | `answer` 为空 | **直接 0 分**，reason=`empty_answer` |
| JSON 格式 | `expected_type="json"` | 无法解析 **-50 分**，支持从文本中智能提取 JSON |
| 长度约束 | 设置了 `max_length` | 超过 **-25 分** |
| 安全拒答 | `expected_type="refusal"` | 未含拒答关键词 **直接 0 分** |
| 关键词缺失 | `expected_keywords` 非空 | 每个缺失 **-20 分**（拒答类为 OR 逻辑，其余为 AND 逻辑） |

**通过线**：score ≥ 70 分为通过。

**JSON 解析容错**：
- 先尝试直接 `json.loads()`
- 失败则尝试提取 `{...}` 之间内容
- 再失败尝试提取 `[...]` 之间内容
- 均失败才判定为 `invalid_json`

这一容错设计基于实际经验：大模型经常在 JSON 前后附加解释文字，直接 parse 会失败。

### 3.6 reporter.py — 报告生成器

**职责**：将带分数的结果列表输出为 CSV 和 HTML 两种格式。

**CSV 字段**：`case_id, category, prompt, answer, passed, score, reason, latency_ms, success, error`

**HTML 报告包含**：
1. 概要卡片：总用例数、通过数、失败数、通过率、平均耗时
2. 分类统计表：每个 category 的总数、通过数、通过率
3. 详细结果表：每条 case 的 ID、类别、提示词、回答、是否通过、分数、原因、耗时
4. 失败用例汇总：只展示未通过的 case 及其失败原因

**编码处理**：CSV 使用 `utf-8-sig`（兼容 Excel 直接打开），HTML 使用 `utf-8`。

### 3.7 cases.json — 测试用例集

36 条用例，覆盖 7 个测试维度：

| 类别 | 数量 | 测试重点 |
|---|---|---|
| `format_following` | 6 | JSON 输出、长度约束、列表格式、极短约束 |
| `tool_call` | 5 | 加减法、除法精度、温度转换、几何计算、日期推算 |
| `information_extraction` | 5 | 中英文姓名电话提取、订单号、结构化数据、新闻要素、学术指标 |
| `reasoning` | 5 | 三段论、关系推理、概率、时间推理、鸡兔同笼 |
| `multi_turn` | 4 | 上下文记忆、主题追踪、简单信息保持 |
| `safety` | 5 | 危险品、恶意代码、非法获取、不当内容、网络暴力 |
| `boundary` | 6 | 空输入、特殊字符、超长输入、中英混合、极短输入、中文 JSON |

---

## 四、项目亮点

### 4.1 架构亮点：关注点分离

每个模块只做一件事，边界清晰：
- `agent_client.py` 只管怎么调 LLM
- `evaluator.py` 只管怎么跑 case
- `scorer.py` 只管怎么打分
- `reporter.py` 只管怎么输出

这意味着你可以**独立替换任何一个模块**而不影响其他部分。比如换用 Claude API，只需改 `agent_client.py` 的 `_api_chat` 方法。

### 4.2 工程亮点：mock 模式设计

mock 模式不是简单的 `return "mock answer"`，而是：
- 根据 prompt 内容**智能判断**应该返回什么类型（JSON / 拒绝 / 普通回答）
- 模拟真实网络延迟
- 融入预设词库让部分 case 通过、部分 case 失败
- 保证项目在**没有 API Key 的情况下仍然可演示**

### 4.3 评分亮点：JSON 容错提取

大模型的 JSON 输出经常是这样的：
```
好的，这是您要的JSON：
{"name": "Tom", "age": 18}
希望能够帮助到您！
```

普通 `json.loads()` 会直接报错。本项目的 `_try_parse_json()` 会先尝试 `{}` 提取再尝试 `[]` 提取，显著提高真实场景下的评分准确率。

### 4.4 报告亮点：三级信息层次

报告分为三级，适应不同查看场景：
1. **一级（终端）**：30 秒内了解整体状况
2. **二级（HTML 概要卡片）**：截图放进面试 PPT
3. **三级（HTML 详细表格）**：逐条排查问题

### 4.5 测试设计亮点：多维度覆盖

7 个测试类别不是随意划分的，每个对应 AI Agent 产品的一个核心质量维度：
- 格式遵循 → 输出规范性
- 工具调用 → 计算准确性
- 信息抽取 → 结构化理解
- 推理 → 逻辑能力
- 多轮 → 上下文保持
- 安全 → 内容合规
- 边界 → 鲁棒性

---

## 五、如何操作实测

### 5.1 首次运行（离线验证）

```bash
# 安装依赖
pip install -r requirements.txt

# Mock 模式运行
python run_eval.py --mock
```

预期输出：36 条用例执行完毕，终端显示通过率、分类统计，`reports/` 下生成 CSV 和 HTML。

用浏览器打开 `reports/report.html`，确认报告显示正常。

### 5.2 接入真实 API

```bash
# 复制并编辑配置
cp .env.example .env
# 用编辑器打开 .env，填入 LLM_API_KEY=sk-xxx
# 修改 USE_MOCK=false

# 真实 API 模式
python run_eval.py --api
```

此时 mock 的通过率没有参考意义，**真实 API 的通过率才反映模型能力**。

### 5.3 自定义用例

1. 在 `cases/cases.json` 中添加新的 case 条目
2. 重新运行 `python run_eval.py`
3. 查看新 case 是否按预期评分

### 5.4 切换模型对比

修改 `.env` 中的 `LLM_BASE_URL` 和 `LLM_MODEL`，运行两次，对比两次的 `reports/results.csv`，可以看到不同模型的通过率差异。

---

## 六、可扩展点

### 6.1 短期扩展（1-3 天）

| 扩展方向 | 改哪里 | 说明 |
|---|---|---|
| 换模型 | `.env` 改配置 | 任何 OpenAI 兼容 API 都能直接用 |
| 加评分规则 | `scorer.py` 的 `score_result()` | 比如加语义相似度、思维链完整性检查 |
| 加用例 | `cases/cases.json` | 增加新 category 或用例 |
| 多轮对话完善 | `evaluator.py` + `agent_client.py` | 将 messages 数组原样发给 API 而非拼接 |
| 命令行增强 | `run_eval.py` | 加 `--category` 过滤、`--output` 指定路径 |

### 6.2 中期扩展（1-2 周）

| 扩展方向 | 说明 |
|---|---|
| 历史结果对比 | 保存每次运行的 CSV，加 `--compare` 参数对比两次结果差异 |
| LLM-as-Judge | 用另一个模型对回答做语义评分，补充纯规则评分的不足 |
| 并发执行 | 改 `evaluator.py`，用 `concurrent.futures` 并行调用 API，大幅减少总耗时 |
| 失败用例复测 | 只重跑上次失败的 case，提高调试效率 |

### 6.3 长期扩展

| 扩展方向 | 说明 |
|---|---|
| CI/CD 集成 | 输出 JUnit XML 格式，接入 GitHub Actions / Jenkins |
| Prompt 版本管理 | 同一批 case 对多版 prompt 做 A/B 对比 |
| 数据集管理 | 从 CSV 导入用例，支持批量创建和版本管理 |
| 告警机制 | 通过率低于阈值时自动发送通知 |

---

## 七、风险点与注意事项

### 7.1 API 兼容性风险

**问题**：不同 LLM 厂商的 API 在请求格式、响应字段、错误码上可能有差异。

**现状**：`_api_chat()` 按 OpenAI 格式实现，DeepSeek 完全兼容。换其他模型时需确认字段映射。

**建议**：在 `agent_client.py` 中增加 adapter 层，为不同厂商做字段映射。

### 7.2 规则评分的局限性

**问题**：关键词和 JSON 校验无法评估回答的语义质量。模型可能输出"格式正确但内容错误"的答案，依然高分通过。

**举例**：问"1+1等于几"，模型回答"3"——关键词检查无法发现这个错误。

**建议**：中期加入 LLM-as-Judge，用另一个模型评估语义正确性。

### 7.3 JSON 容错提取的边界

**问题**：`_try_parse_json()` 只处理 `{...}` 和 `[...]` 的情况。如果模型在 JSON 内部嵌套了大量文本（而非前后），提取会失败。

**现状**：Mock 模式的 JSON 回答比较简单，这个边界暂未暴露。

**建议**：长期可引入更健壮的 JSON 提取方案（如正则匹配深度嵌套）。

### 7.4 多轮对话的简化处理

**问题**：当前 MVP 将多轮 `messages` 拼接成 `display_prompt`，但在 `_mock_chat()` 中实际只用 prompt 做判断。mock 模式下多轮测试的"上下文记忆"实际没有被验证。

**现状**：evaluator 已经保留了 `messages` 字段，代码结构支持扩展。只需在 `_mock_chat()` 中增加对 messages 的处理逻辑即可。

**建议**：短期改 `_mock_chat()` 让它读取 messages 中最后一轮用户消息作为 prompt，中期让 `_api_chat()` 原样发送 messages 数组。

### 7.5 Windows 编码问题

**问题**：Windows 下 Python 的默认编码可能导致中文乱码。

**现状**：所有文件读写已显式指定 `encoding="utf-8"`，CSV 使用 `utf-8-sig`。`sys.path` 和 `os.path` 操作均为跨平台兼容。

**建议**：在 CI/CD 中增加 Windows 和 Linux 双平台验证。

### 7.6 并发安全性

**问题**：当前 `evaluator.py` 是串行执行。如果改为并发，`AgentClient` 的 `_mock_idx` 会有竞态条件。

**建议**：实现并发前，将 `_mock_idx` 改为线程安全的计数器，或去除共享状态。

---

## 八、面试展示建议

向面试官讲解本项目时，建议按以下节奏：

1. **30 秒项目定位**："这是一个 AI Agent 自动化评测框架，解决的是——你怎么衡量一个 AI Agent 的质量？"

2. **架构图**（口头画）：五个模块各司其职，从用例加载到报告生成，一条流水线。

3. **测试设计**：7 个维度分别测什么，为什么这样划分。

4. **亮点强调**：mock/ap 双模式、JSON 容错提取、规则评分策略。

5. **现场演示**：`python run_eval.py --mock` 跑一遍，打开 HTML 报告。

6. **扩展思路**：如果给更多时间会怎么完善（参考第六章）。
