import json
import os

REQUIRED_FIELDS = ["case_id", "category"]
OPTIONAL_FIELDS = ["prompt", "expected_type", "expected_keywords", "max_length", "description", "messages"]
VALID_CATEGORIES = [
    "format_following", "tool_call", "information_extraction",
    "reasoning", "multi_turn", "safety", "boundary",
]


class CaseLoadError(Exception):
    pass


def load_cases(file_path="cases/cases.json"):
    if not os.path.exists(file_path):
        raise CaseLoadError(f"Case file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise CaseLoadError("cases.json must contain a JSON array")

    cases = []
    for i, item in enumerate(raw):
        errors = _validate_case(item, i)
        if errors:
            raise CaseLoadError(f"Case #{i}: {'; '.join(errors)}")

        case = {
            "case_id": item["case_id"],
            "category": item["category"],
            "prompt": item.get("prompt", ""),
            "expected_type": item.get("expected_type", "text"),
            "expected_keywords": item.get("expected_keywords", []),
            "max_length": item.get("max_length"),
            "description": item.get("description", ""),
            "messages": item.get("messages"),
        }
        cases.append(case)

    return cases


def _validate_case(item, index):
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in item or not item[field]:
            errors.append(f"missing required field '{field}'")

    if "category" in item and item["category"] not in VALID_CATEGORIES:
        errors.append(f"unknown category '{item['category']}'")

    if "prompt" not in item and "messages" not in item:
        errors.append("must have 'prompt' or 'messages'")

    return errors
