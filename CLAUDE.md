# AgentEval - AI Agent Automated Testing Demo

面向 AI Agent 产品的轻量级自动化评测框架。Python 3.10+，只依赖 `requests` 和 `python-dotenv`。

## Tech Stack
- Python 3.10+
- requests (HTTP), python-dotenv (env config)
- LLM API: DeepSeek / OpenAI-compatible (mock mode available offline)

## Project Structure
- `run_eval.py` — main entry, wires everything together
- `src/agent_client.py` — `AgentClient` class, mock + api dual mode
- `src/case_loader.py` — load & validate cases from JSON
- `src/evaluator.py` — `Evaluator` class, batch execution engine
- `src/scorer.py` — rule-based scoring (keywords, JSON validation, length, safety refusal)
- `src/reporter.py` — CSV + HTML report generation
- `cases/cases.json` — 36 test cases across 7 categories
- `reports/` — output directory for results.csv and report.html

## Development Commands
- Install: `pip install -r requirements.txt`
- Run (mock): `python run_eval.py --mock`
- Run (api): `python run_eval.py --api`
- Custom cases: `python run_eval.py --case-file cases/cases.json`

## Critical Conventions
- No web frameworks, databases, or complex deps — keep it lightweight
- Mock mode must always work without API key
- Scoring threshold: score >= 70 = passed
- All output files use UTF-8 encoding (CSV uses utf-8-sig for Excel compat)
- See `gpt_guide.txt` for full project specification and resume goals
