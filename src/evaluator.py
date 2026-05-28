class Evaluator:
    """Batch execution engine for test cases."""

    def __init__(self, client):
        self.client = client

    def run(self, cases):
        """Execute all test cases and return results list."""
        results = []
        for case in cases:
            result = self._run_one(case)
            results.append(result)
        return results

    def _run_one(self, case):
        prompt = case.get("prompt", "")
        messages = case.get("messages")
        display_prompt = prompt or self._build_prompt_from_messages(messages)

        if messages:
            answer, latency_ms, success, error = self.client.chat(display_prompt, messages=messages)
        else:
            answer, latency_ms, success, error = self.client.chat(display_prompt)

        return {
            "case_id": case["case_id"],
            "category": case["category"],
            "prompt": display_prompt,
            "messages": messages,
            "answer": answer,
            "latency_ms": latency_ms,
            "success": success,
            "error": error,
            "expected_type": case.get("expected_type", "text"),
            "expected_keywords": case.get("expected_keywords", []),
            "max_length": case.get("max_length"),
            "description": case.get("description", ""),
        }

    @staticmethod
    def _build_prompt_from_messages(messages):
        if not messages:
            return ""
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            parts.append(f"[{role}]: {content}")
        return " | ".join(parts)
