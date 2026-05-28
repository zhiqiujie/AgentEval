import os
import time
import random
import requests
from dotenv import load_dotenv

load_dotenv()

MOCK_WORD_BANK = [
    "Hello", "World", "test", "data", "result", "answer", "query", "response",
    "model", "agent", "evaluation", "score", "output", "input", "system",
    "Tom", "18", "小明", "李华", "北京", "中国",
    "Python", "code", "function", "class", "object", "module", "import",
]

MOCK_JSON_RESPONSES = [
    '{"name": "Tom", "age": 18}',
    '{"name": "Tom","age":18}',
    'some text before {"name": "Tom", "age": 18} and after',
]

MOCK_REFUSAL_RESPONSES = [
    "抱歉，我无法帮助你完成这个请求，因为这涉及违法内容。",
    "我不能回答这个问题，这不符合安全规范。",
    "对不起，不可以提供这类信息。",
]

MOCK_NORMAL_RESPONSES = [
    "Tom, 18岁，来自北京。",
    "小明是我的名字。",
    "Python是一种广泛使用的编程语言，具有简洁的语法和丰富的库。",
    "1+1等于2。",
    "今天天气很好，适合出门散步。",
    "人工智能正在改变世界。",
    "The answer is 42.",
    "我可以帮助你完成这个任务。",
    "请提供更多信息以便我更好地回答。",
    "这是一个很好的问题。",
]


class AgentClient:
    """LLM API client with mock and real API modes."""

    def __init__(self, use_mock=None, api_key=None, base_url=None, model=None, timeout=None):
        self.use_mock = use_mock if use_mock is not None else os.getenv("USE_MOCK", "true").lower() == "true"
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-chat")
        self.timeout = int(timeout or os.getenv("REQUEST_TIMEOUT", "30"))
        self._mock_idx = 0

    def chat(self, prompt, messages=None):
        """Send a request and return (answer, latency_ms, success, error)."""
        if self.use_mock:
            return self._mock_chat(prompt)

        return self._api_chat(prompt, messages)

    def _mock_chat(self, prompt):
        latency = random.randint(50, 300)
        time.sleep(latency / 1000.0)

        prompt_lower = prompt.lower()

        # Detect JSON format requirement
        if "json" in prompt_lower and ("只返回" in prompt or "only" in prompt_lower or "不要输出其他" in prompt):
            resp = random.choice(MOCK_JSON_RESPONSES)
        elif "json" in prompt_lower:
            resp = random.choice(MOCK_JSON_RESPONSES + MOCK_NORMAL_RESPONSES)
        # Detect safety/refusal
        elif any(kw in prompt for kw in ["违法", "攻击", "恶意", "色情", "暴力", "非法", "hack", "attack"]):
            resp = random.choice(MOCK_REFUSAL_RESPONSES)
        else:
            resp = random.choice(MOCK_NORMAL_RESPONSES)

        # Rotate through word bank for keyword-matching tests
        if self._mock_idx < len(MOCK_WORD_BANK):
            resp += " " + MOCK_WORD_BANK[self._mock_idx]
            self._mock_idx += 1

        return resp, latency, True, None

    def _api_chat(self, prompt, messages=None):
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(messages, list) and all(isinstance(m, dict) for m in messages):
            pass
        else:
            messages = [{"role": "user", "content": prompt}]

        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            latency_ms = (time.perf_counter() - t0) * 1000
            if resp.status_code == 200:
                data = resp.json()
                answer = data["choices"][0]["message"]["content"]
                return answer, round(latency_ms, 2), True, None
            else:
                error_msg = f"API returned status {resp.status_code}: {resp.text[:200]}"
                return "", round(latency_ms, 2), False, error_msg
        except requests.exceptions.Timeout:
            latency_ms = (time.perf_counter() - t0) * 1000
            return "", round(latency_ms, 2), False, "timeout"
        except requests.exceptions.ConnectionError as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            return "", round(latency_ms, 2), False, f"connection_error: {e}"
        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            return "", round(latency_ms, 2), False, f"unknown_error: {e}"
