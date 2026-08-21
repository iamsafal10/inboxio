# System Flow
## Phase 0: Foundations & Project Scaffolding
- **Package Architecture**:
  - `app/core`: Application settings (`config.py`), database session dependency (`database.py`), security utilities (`security.py`), crypto helpers (`crypto.py`), and auth dependencies (`deps.py`).
  - `app/models`: Domain schemas and SQLAlchemy ORM models (`user.py`, `profile.py`, `email_indexed.py`, `memory_fact.py`, `eval_result.py`).
  - `app/routers`: FastAPI endpoint controllers (`auth.py`, `gmail.py`) and schema definitions (`schemas.py`).
  - `app/services`: Integrations (`gmail_oauth.py`, Vector DB, LLM orchestrators).
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
- **Gmail OAuth Connect & Token Storage Flow**:
  1. Authenticated user requests Google consent URL via `GET /gmail/oauth/connect`.
  2. `gmail_oauth.py` generates a PKCE `code_verifier`, encrypts `user_id` + `code_verifier` into the `state` parameter, and constructs Google authorization URL with read-only scopes (`gmail.readonly`, `openid`, `userinfo.email`).
  3. User completes Google consent in browser and is redirected to `GET /gmail/oauth/callback?code=...&state=...`.
  4. Backend decrypts `state` to extract `user_id` and the PKCE `code_verifier`.
  5. `exchange_code_for_tokens()` exchanges `code` and `code_verifier` with Google's token endpoint.
  6. Access and refresh tokens are symmetrically encrypted via Fernet (`app/core/crypto.py`) and stored in the `users` table along with token expiry and `gmail_connected = True`.
  7. User is redirected to `/gmail/connected` confirming successful link.
- **Minimal Web Chat UI Flow (Phase 0 Stub)**:
  1. Client loads `GET /chat-ui` to receive the single-page HTML interface.
  2. User logs in, storing the returned JWT strictly in memory (JavaScript variable).
  3. Client checks `GET /auth/me` to determine Gmail connection status.
  4. User sends a message via `POST /chat`, protected by the `get_current_user` dependency.
  5. The backend echoes a placeholder response (Note: `/chat` is intentionally a stub to be replaced with real LLM/Agent logic in Phase 2).
