# System Flow
## Phase 0: Foundations & Project Scaffolding
- **Package Architecture**:
  - `app/core`: Application settings (`config.py`), database session dependency (`database.py`), security utilities (`security.py`), and auth dependencies (`deps.py`).
  - `app/models`: Domain schemas and SQLAlchemy ORM models (`user.py`, `profile.py`, `email_indexed.py`, `memory_fact.py`, `eval_result.py`).
  - `app/routers`: FastAPI endpoint controllers (`auth.py`) and schema definitions (`schemas.py`).
  - `app/services`: Integrations (Gmail, Vector DB, LLM orchestrators).
  - `app/main.py`: ASGI entrypoint exposing application routes and root health check (`GET /`).
  - `alembic`: Database migration environment and versioned migration scripts.
- **Configuration Flow**: Centralized `Settings` loaded via `pydantic-settings` from environment / `.env`, ensuring consistent access across services and routers.
- **Database Session Flow**:
  1. `app.core.database.engine` connects to PostgreSQL via `settings.DATABASE_URL`.
  2. `SessionLocal` creates scoped session instances.
  3. `get_db()` FastAPI dependency yields session to route handlers and ensures cleanup in `finally` blocks.
  4. Alembic `env.py` dynamically loads `settings.DATABASE_URL` and `Base.metadata` to support automated migrations.
- **Authentication & JWT Token Flow**:
  1. User registers via `POST /auth/signup` with email & password.
  2. Password is salted and hashed using `bcrypt` before writing to the `users` table.
  3. A signed JWT access token (`HS256`) containing the user's UUID is returned.
  4. On subsequent requests, the client passes `Authorization: Bearer <token>`.
  5. `get_current_user` FastAPI dependency decodes the token, verifies signature and expiration, and fetches the authenticated `User` from PostgreSQL.
  6. `POST /auth/login` supports both JSON payloads and form-encoded data for full Swagger UI OAuth2 Password Flow compatibility.
