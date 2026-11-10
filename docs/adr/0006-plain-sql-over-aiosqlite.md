# Plain SQL over aiosqlite with numbered migrations

The backend talks to SQLite with hand-written, parameterised SQL through `aiosqlite`, behind one repository Protocol per aggregate. The schema is a series of numbered SQL migration files tracked with `PRAGMA user_version`. The schema is small (about six tables) and its needs are simple, while the job ad lists SQL and the interview covers databases. Writing the SQL by hand puts that skill in plain view, and the repository seam keeps an ORM a local change if it's ever needed.

## Considered Options

- **SQLAlchemy ORM or SQLModel.** The most standard choice and the least CRUD code. Rejected: it hides the SQL the reviewers want to see, lazy loading can surprise you, and SQLModel merges DB models with API DTOs, which ADR 0005 rules out.
- **SQLAlchemy Core.** Composable queries that still read like SQL. Rejected: a dependency and an API to learn, to save about ten lines of dynamic `WHERE` for the incident list filters.
- **Sync `sqlite3`.** Either sync `def` endpoints in FastAPI's threadpool, with async services calling repositories through `run_in_threadpool`, or sync calls straight from async code. Rejected: the first mixes two styles and complicates ADR 0005's `asyncio.Lock`, and the second blocks the event loop. `aiosqlite` keeps the same SQL and the `sqlite3` API, with `await`.
- **A `schema.sql` of `CREATE TABLE IF NOT EXISTS`.** Rejected: it can't change an existing table, and the Pi deploy keeps its database on a volume across releases.
- **Alembic.** Rejected: its main benefit, autogenerate, needs SQLAlchemy models. Without them it's a heavier version of numbered SQL files. It becomes the right choice once there's an ORM or a team.
- **Commit inside each repository method**, or **one transaction per HTTP request**. Rejected: the first lets multi-step writes half-succeed, for example the default-vehicle swap. The second would hold a write transaction for a whole AI turn (up to ~100 s, ADR 0004).
- **One shared connection for the app.** Rejected: concurrent requests would interleave inside each other's transactions.
- **A generic `Repository[T]` base.** Rejected: the aggregates differ (AI turns are append-only, the nearby snapshot is replace-only), so shared CRUD fits poorly.
- **Normalised tables for the AI payload, inputs snapshot and nearby places.** Rejected: they're immutable documents, read whole and never queried inside, so child tables would add joins and nothing to query.
- **Validation only in Pydantic.** Rejected: the database is the last line of defence, and ADR 0005 already relies on a UNIQUE constraint to settle the idempotency race.
- **`:memory:` databases in tests.** Rejected: each connection to `:memory:` is a separate, empty database, so a connection per request would see no schema, and `:memory:` can't run WAL. Tests would take a different code path from production.

## Consequences

- **Layers.** Routers → services → repositories. Each aggregate (Vehicle; Incident with its photos, AI turns and nearby snapshot; the damage report) has a `typing.Protocol` with `async def` methods and one `Sqlite…` implementation. Repositories return domain dataclasses, never `sqlite3.Row`, so nothing above them knows about SQL. DB rows, domain objects and API DTOs are three separate things.
- **The service owns the unit of work.** Connections run in autocommit mode, and the unit of work opens `BEGIN IMMEDIATE`, which takes the write lock up front so two writers can't fail with SQLITE_BUSY halfway through. Repositories never commit. No transaction stays open across a network call: an AI turn reads, commits, calls the LLM, then writes in a short transaction.
- **A connection per request** comes from a FastAPI `yield` dependency. Every connection sets `PRAGMA foreign_keys = ON` (without it, ADR 0001's CASCADE and SET NULL silently do nothing), `journal_mode = WAL` (reads don't block the writer during an AI turn) and `busy_timeout = 5000`.
- **The schema enforces its own rules.**
  - Every table is `STRICT`.
  - Enums (`status`, `kind`, `spare_wheel`, …) and 0/1 booleans have `CHECK` constraints. A test keeps the SQL enum lists and the Pydantic enums in sync.
  - "At most one default vehicle" is a partial unique index: `CREATE UNIQUE INDEX one_default_vehicle ON vehicles(is_default) WHERE is_default = 1`. The swap runs "unset old, set new" in one transaction.
  - FKs and `incidents(created_at)` are indexed.
  - Ids are `INTEGER PRIMARY KEY` (ADR 0005).
- **Whole documents as JSON `TEXT`.** The AI turn `payload`, the inputs snapshot and the nearby `places` are `TEXT` with `CHECK (json_valid(col))`, parsed by Pydantic in the repository. Anything filtered or joined on (`status`, `vehicle_id`, `incident_id`, `seq`, `kind`) is a real column.
- **Timestamps** are `TEXT` in ISO 8601 UTC with a fixed format (`2026-11-10T12:00:00.000Z`), set by the application, never `DEFAULT CURRENT_TIMESTAMP`. Text order is then time order, and the values match ADR 0005's wire format.
- **Migrations** are forward-only files `migrations/NNNN_<name>.sql`. Each one runs in its own transaction that also sets `user_version` to its number. They run at startup (FastAPI lifespan) and through `python -m app.db migrate`, which call the same function. The database file comes from `DATABASE_PATH`, on a named docker volume next to `UPLOAD_DIR`.
- **Fail fast on old SQLite.** `STRICT` needs SQLite 3.37 or newer. Startup and `python -m app.db migrate` check `sqlite3.sqlite_version` and stop with a clear message naming the found and required versions if it's older.
- **Tests run on a fresh temporary file database per test** (pytest `tmp_path`, migrations applied), so they use the same connection dependency, pragmas and WAL as production. They hit the real SQL and constraints. One test proves the FK cascades and SET NULL actually fire. Fakes of the Protocols are only for service tests that care about behaviour, not storage.
