# Backend Agent Instructions

Read the repository root `AGENTS.md` first. Backend implementation follows:

- Source directory: `backend/`
- Run API locally: `uvicorn main:app --reload`
- Lint: `ruff check .`
- Format: `black .`
- Type check: `mypy .`
- Tests: `pytest`

Rules:

- All public functions, Pydantic models, and Agent entrypoints need type annotations.
- LangGraph state must be Pydantic v2 models, not untyped dict contracts.
- Every Agent node must produce trace data with prompt/input/output/token/cost/latency fields.
- Do not hardcode secrets. Use `.env` locally and keep `.env.example` value-only-empty.
- CI and tests use mock LLM behavior by default.
