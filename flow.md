# System Flow
## Phase 0: Foundations & Project Scaffolding
- **Package Architecture**:
  - `app/core`: Application settings (`config.py`) and database engine/session dependency (`database.py`).
  - `app/models`: Domain schemas and SQLAlchemy ORM models (`user.py`, `profile.py`, `email_indexed.py`, `memory_fact.py`, `eval_result.py`).
  - `app/routers`: FastAPI endpoint controllers.
  - `app/services`: Integrations (Gmail, Vector DB, LLM orchestrators).
  - `app/main.py`: ASGI entrypoint exposing application routes and root health check (`GET /`).
  - `alembic`: Database migration environment and versioned migration scripts.
- **Configuration Flow**: Centralized `Settings` loaded via `pydantic-settings` from environment / `.env`, ensuring consistent access across services and routers.
- **Database Session Flow**:
  1. `app.core.database.engine` connects to PostgreSQL via `settings.DATABASE_URL`.
  2. `SessionLocal` creates scoped session instances.
  3. `get_db()` FastAPI dependency yields session to route handlers and ensures cleanup in `finally` blocks.
  4. Alembic `env.py` dynamically loads `settings.DATABASE_URL` and `Base.metadata` to support automated migrations.
