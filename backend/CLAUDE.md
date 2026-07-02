# Backend Agent Instructions

Read the repository root `AGENTS.md` first. Backend implementation follows:

- Source directory: `backend/`
- Run API locally: `python run.py` (selects a psycopg-compatible event loop per-platform). Plain `uvicorn main:app --reload` works on Linux; on Windows it must be `uvicorn main:app --reload --loop main:selector_event_loop`, otherwise psycopg fails with `Psycopg cannot use the 'ProactorEventLoop'`.
- Lint: `ruff check .`
- Format: `black .`
- Type check: `mypy .`
- Unit tests: `pytest -m unit`
- PostgreSQL/Redis integration tests: `pytest -m integration`
- Dedicated remote smoke tests: `pytest -m smoke`
- Branch coverage: `pytest --cov=. --cov-branch`

Integration tests only read `TEST_DATABASE_URL` / `TEST_REDIS_URL`; smoke tests only read
`SMOKE_DATABASE_URL` / `SMOKE_REDIS_URL`. Never point these variables at production services.
Start local dependencies from the repository root with
`docker compose -f docker-compose.test.yml up -d` when Docker Compose is available.

Rules:

- All public functions, Pydantic models, and Agent entrypoints need type annotations.
- LangGraph state must be Pydantic v2 models, not untyped dict contracts.
- Every Agent node must produce trace data with prompt/input/output/token/cost/latency fields.
- Do not hardcode secrets. Use `.env` locally and keep `.env.example` value-only-empty.
- CI and tests use mock LLM behavior by default. Real PDF rendering runs only in smoke.
