# Backend Database

`schema.sql` is the S1 database contract for Neon Postgres. It mirrors PRD §十 and is intentionally dependency-light so it can be reviewed before Alembic is installed.

Next step:

1. Install backend dependencies.
2. Convert `schema.sql` into Alembic revision `0001_initial`.
3. Wire `RunManager`, traces, reports, claims, and survey uploads to SQLAlchemy repositories.
