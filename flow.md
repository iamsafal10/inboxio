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
- **Evaluation Reference Lock-in (Task 6)**:
  1. Ran the baseline against 5 real inbox questions covering lookup, summarization, cross-referencing, implied deadlines, and contradictions.
  2. Saved the exact outputs and human judgments to `app/baseline/reference_results.json`.
  3. This file acts as a locked unit test for the Phase 2 LangGraph agent.

## Phase 2: Core Agent Reasoning
- **LangGraph Scaffold & State Flow (Task 1)**:
  1. Initiated a new isolated module (`app/agent/graph.py`) containing the LangGraph structure.
  2. Uses a `TypedDict` (`AgentState`) carrying the user ID, original question, sub-goals, retrieved chunks, conflicts, and final answer.
  3. Nodes execute in sequence: Planner → Tool Selector → Retriever → Conflict Checker → (Loop back OR Synthesizer).
  4. A conditional edge allows looping back from Conflict Checker to Tool Selector for multi-hop reasoning.
- **Planner Node (Task 2)**:
  1. Replaced the stub planner with a real LLM call to Gemini (`gemini-3.5-flash`).
  2. Uses Langchain's structured output (`with_structured_output`) and a Pydantic model (`PlannerOutput`) to guarantee a clean list of sub-goals.
  3. Handles simple lookup questions (1 sub-goal) and complex reasoning (multiple sub-goals).
  4. Implements a retry-then-fail mechanism for malformed outputs to prevent passing corrupted state to downstream nodes.
- **Tool Selector Node & Retrieval Tools (Task 3)**:
  1. Implemented three specialized retrieval tools in `app/services/retrieval_tools.py`: `search_by_sender`, `reconstruct_thread`, and `search_by_date_range`.
  2. All tools return the standard chunk dictionary shape (with `distance=None` for DB queries) for uniform downstream processing.
  3. Replaced the `tool_selector` stub with a basic LLM-powered router that inspects sub-goals and outputs a typed `ToolSelectionList`, routing to the most appropriate tool or defaulting to `semantic_search`.
- **Infrastructure Hardening (Pre-Task 4)**:
  1. Configured hard maximum (`MAX_EMAILS=25`) for email ingestion in `app/core/config.py`.
  2. Implemented a deterministic domain filter (`domain_filter.py`) operating with zero LLM calls. The filter strictly gates emails at the ingestion layer (fetching -> filtering -> discarding non-career emails) and questions at the query layer (`chat_endpoint`), ensuring irrelevant data never reaches ChromaDB or the LLM.
  3. Added an LLM-agnostic instantiation mechanism (`app/llm/llm_setup.py`) to swap models via the `LLM_PROVIDER` environment variable, enabling `stealth/ox-alpha` via OpenRouter alongside Gemini and Groq.
  4. Extensively verified that retrieval tools (semantic search, sender, thread, date-range) make zero LLM calls.
  5. Enforced LLM provider traceability by creating an Alembic migration that adds a `provider` tracking column to all persisting models (`EvalResult`, `MemoryFact`, `Profile`).

- **Task 4: Real Contradiction Checking**:
  1. Replaced the `conflict_checker` stub with a real `conflict_checker_node` that aggregates retrieved chunks.
  2. Implemented batching logic (splitting context by 30,000 character boundaries) to support analyzing large evidence sets that exceed context limits.
  3. Uses `with_structured_output(ConflictOutput)` to extract structured contradictions (`has_contradictions`, plus a list of `claim_a`, `claim_b`, `source_a`, `source_b`).
  4. Introduced an explicit failure state (`check_status = "failed"`) if the LLM API exhausts retries, distinguishing real failures from a genuine "no contradiction" result.

- **Task 5: Citation-Aware Synthesis**:
  1. Replaced the `synthesizer` stub with a real `synthesizer_node` completing the full graph (plan → tool-select → retrieve → conflict-check → synthesize).
  2. Generates comprehensive answers using inline citations formatted as `[Source ID]` (e.g., `[1]`).
  3. Uses `with_structured_output(SynthesisOutput)` to enforce citations and return a separate, mapped structured list of `Citation` models for UI rendering.
  4. Prompt enforces surfacing known contradictions explicitly and prepending a disclaimer if `check_status == "failed"`.

- **Task 6: Locked Eval Question Set**:
  1. Created a fixed, permanent evaluation set (`eval/eval_questions.json`) tailored directly to the user's real ingested inbox data.
  2. The set contains 10 rigorous queries spanning multi-hop analysis, contradiction handling (verifying no false positives), implied risk/silence deduction, and single-lookup sanity checks.
  3. This locked set is entirely content-based and will serve as the definitive benchmark for the final evaluation script in Task 7.

## Phase 3: Memory

- **Task 1: Memory Schema**:
  1. Designed the database schema for long-term durable memory (`MemoryFact`), including `fact_type`, `source`, and a boolean `active` flag for deletion testing.
  2. Generated and applied Alembic migrations.
  3. Updated the LangGraph agent state (`AgentState`) to include `chat_history` for short-term, session-scoped context.
  4. Created DB constraint unit tests for the schema.

- **Task 2: Short-term Memory**:
  1. Implemented a session history store (`SESSION_HISTORY`) in `graph.py` keyed by `user_id` to persist conversation turns across agent invocations.
  2. Modified `planner_node` and `synthesizer_node` to inject the `chat_history` into their prompts, enabling the agent to resolve conversational references (e.g., "what about the other one?").
  3. Applied a rolling window cap of 6 messages (3 full turns) to prevent unbounded context growth and API exhaustion.
  4. Added `test_short_term_memory.py` to assert memory accumulation, capping, and cross-user isolation.

- **Task 3: Long-term Memory Writes**:
  1. Created `app/agent/memory_writer.py` containing `extract_and_store_facts(user_id, db)`.
  2. Instructed the LLM (via structured outputs) to conservatively extract durable personal facts and ignore speculative or ephemeral details from the session history.
  3. Added exact-match `fact_text` deduplication logic before persisting to `memory_facts`.
  4. Wrote unit tests confirming extraction reliability and deduplication logic, as well as a live test script (`test_memory_writer_live.py`) visually demonstrating the agent ignoring non-durable details.
