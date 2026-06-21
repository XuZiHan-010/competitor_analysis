import asyncio

from sqlalchemy import text

from api.dependencies import run_manager
from db.session import create_engine
from main import selector_event_loop


async def _check() -> None:
    eng = create_engine()
    async with eng.connect() as conn:
        val = (await conn.execute(text("SELECT 1"))).scalar_one()
        print("SQLAlchemy async engine SELECT 1 ->", val)
    await eng.dispose()

    # raw psycopg AsyncConnectionPool path (services/runs/manager.py)
    runs = await run_manager.list_runs(limit=1, user_id=None)
    print("raw psycopg pool list_runs ok, rows:", len(runs))


with asyncio.Runner(loop_factory=selector_event_loop) as r:
    print("loop ->", type(r.get_loop()).__name__)
    r.run(_check())
print("VERIFY OK: psycopg connected on SelectorEventLoop")