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
- **Phase 0 Test Audit**:
  - Full suite verified with 16 automated tests.
  - Covers config loading, DB connection/schema mapping, JWT auth flow, Gmail OAuth connect, and the UI stub.

## Phase 1: Ingestion & RAG
- **Gmail Fetcher Flow (Task 1)**:
  1. Initiated via `POST /gmail/sync` for the authenticated user.
  2. Fetches `users.messages.list` from the Gmail API with pagination (`nextPageToken`), up to a configurable `MAX_EMAILS` limit (default 500).
  3. Protects against 429/403 rate limits with a transparent exponential backoff mechanism.
  4. Extracts structural fields (sender, recipient, subject, date) and plain-text body (stripping HTML where necessary).
  5. Writes output to `emails_indexed` in PostgreSQL with `status="fetched"`, explicitly leaving `embedded=False` for downstream chunking.
- **Email Chunker Flow (Task 2)**:
  1. Initiated via `POST /gmail/chunk` for the authenticated user.
  2. Queries `emails_indexed` for all emails belonging to the user where `status="fetched"`.
  3. Splits the raw email `body` into segments (chunks) based on a configurable `MAX_CHUNK_CHARS` threshold (default 2000), prioritizing paragraph boundaries (`\n\n`) over hard character limits.
  4. Attaches vital metadata (gmail message id, thread id, sender, subject, date, and chunk index) to every chunk.
  5. Saves output to a new `chunks` PostgreSQL table with `status="chunked"` and updates the parent email row status to `"chunked"`.
- **Vector Embedding Flow (Task 3)**:
  1. Initiated via `POST /gmail/embed` for the authenticated user.
  2. Queries `chunks` for all un-embedded chunks belonging to the user (`status="chunked"`).
  3. Connects to a local ChromaDB PersistentClient and fetches/creates a strongly isolated collection named `inboxio_user_<user_id>`.
  4. Generates local vector embeddings using `SentenceTransformer` (`all-MiniLM-L6-v2`) in batches.
  5. Stores the embedding vectors in ChromaDB alongside the original text and the duplicated SQL metadata (sender, subject, date, thread_id) to enable standalone filtering and citation.
  6. Updates the processed `chunks` rows in PostgreSQL to `status="embedded"`.
- **Semantic Search Flow (Task 4)**:
  1. Initiated via `POST /gmail/search` containing a natural language `query` and an optional `top_k` parameter (default 5).
  2. Embeds the query using the identical `SentenceTransformer` model (`all-MiniLM-L6-v2`) to ensure vector compatibility.
  3. Connects specifically to the authenticated user's isolated ChromaDB collection (`inboxio_user_<user_id>`).
  4. Executes an L2 distance vector search returning the `top_k` closest chunk matches.
  5. Returns the raw text, distance score, and full metadata (sender, subject, date, thread_id) for each matched chunk without any LLM synthesis.
- **Dumb Baseline RAG Flow (Task 5)**:
  1. Initiated via `POST /baseline/ask` containing a user `question`.
  2. Directly passes the raw question to the Semantic Search tool (Task 4) requesting `top_k=5` chunks.
  3. Formats the returned chunks and metadata into a single, naive context string.
  4. Sends the context and question to the primary LLM (`gemini-3.5-flash`) via `ChatGoogleGenerativeAI` using a strict prompt template that prohibits outside knowledge.
  5. Returns both the generated natural language answer and the raw chunks used, providing a permanent comparative baseline for Phase 2 evaluation.
