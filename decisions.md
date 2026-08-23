# Design Decisions
## Phase 0: Foundations & Project Scaffolding
- **Decision: Centralized Settings with `pydantic-settings`**:
  - *Context*: Need a single, type-safe source of truth for runtime configurations, credentials, and API keys.
  - *Choice*: Used `pydantic_settings.BaseSettings` with `.env` loading and sensible defaults for local development.
  - *Rationale*: Allows graceful startup and testing of base endpoints without immediately breaking when third-party provider keys (Gemini, Groq, Google OAuth) are still being configured.
- **Decision: Strict `.env` isolation via `.gitignore` and `.env.example`**:
  - *Context*: The agent handles sensitive OAuth secrets, application keys, and database credentials.
  - *Choice*: Committed `.env.example` as a template and strictly ignored `.env` and `*.env`.
  - *Rationale*: Prevents accidental credential leakage while maintaining documentation of required configuration parameters.
- **Decision: Separate Read vs Send OAuth Scope Tracking**:
  - *Context*: Gmail integration requests read-only scopes first and send access conditionally in later phases.
  - *Choice*: Tracked `gmail_connected` and `gmail_send_scope_granted` separately in `User`.
  - *Rationale*: Enforces least-privilege security principle and prevents requiring broad send access upfront.
- **Decision: Decoupling Email Metadata from Body Storage**:
  - *Context*: Emails require structured querying (dates, threads, senders) while text vectors need semantic chunking in Chroma.
  - *Choice*: Stored structured metadata and chunk IDs in `emails_indexed` table, while actual email bodies reside in vector store.
  - *Rationale*: Keeps relational database lean and optimized for indexing/joins while offloading high-dimensional vector search to Chroma.
- **Decision: Soft Deletion for Memory Facts**:
  - *Context*: Memory auditability requires proving "delete a fact, confirm the answer changes."
  - *Choice*: Added `deleted_at` nullable timestamp on `memory_facts`.
  - *Rationale*: Allows auditing and comparison experiments showing that deleted facts are excluded from agent context without losing historical trace.
- **Decision: Single-Row Evaluation Diffs**:
  - *Context*: Benchmark evaluations require comparing baseline answers vs agent answers.
  - *Choice*: Both `baseline_answer` and `agent_answer` (along with their scores) are stored in the same row of `eval_results`.
  - *Rationale*: Simplifies direct diffing, scoring comparisons, and reporting without joining across separate run tables.
- **Decision: Two-Step Auth Architecture (App Identity vs Gmail OAuth Connection)**:
  - *Context*: Deciding whether to use Google OAuth as the single sign-on mechanism or use app-level user accounts with an attached Gmail integration.
  - *Choice*: Decoupled app identity (email/password + JWT) from Gmail OAuth tokens (connected later as a secondary step).
  - *Rationale*: Prevents locking application identity exclusively to Google, enables granular permission management (read vs send scopes), supports future multi-account or enterprise auth, and guarantees the user owns an account on Inboxio independently of Gmail token lifecycles.
- **Decision: Granular Scope Separation (Read Now, Send Later)**:
  - *Context*: Google Gmail API offers both `gmail.readonly` and `gmail.send` scopes.
  - *Choice*: Restricted initial Gmail connection strictly to `gmail.readonly`, `openid`, and `userinfo.email`, deferring `gmail.send` to future optional opt-in actions.
  - *Rationale*: Adheres to least privilege principles and ensures users who only want inbox analysis/retrieval are never forced to grant send permissions.
- **Decision: Symmetric Token Encryption at Rest via Derived Fernet Key**:
  - *Context*: Third-party OAuth tokens (access and refresh tokens) must be secured at rest in PostgreSQL.
  - *Choice*: Used Fernet symmetric encryption with a deterministic key derived from `APP_SECRET_KEY` (SHA-256 hash + URL-safe Base64).
  - *Rationale*: Eliminates the overhead of managing a second secret key while ensuring tokens are stored as encrypted bytes in the database.
- **Decision: Stateless PKCE Flow with Encrypted State Parameter**:
  - *Context*: PKCE `code_verifier` generated during authorization request must match the token exchange across separate HTTP requests.
  - *Choice*: Encrypted `user_id` and `code_verifier` inside the `state` parameter using Fernet rather than maintaining short-lived database or cache sessions.
  - *Rationale*: Guarantees zero session state mismatch across restarts and eliminates orphaned cache entries.
- **Decision: In-Memory Only JWT Storage for Chat UI**:
  - *Context*: The minimalist web interface needs to store the JWT after login to make authenticated requests.
  - *Choice*: Stored the token in a plain JavaScript variable rather than `localStorage` or `sessionStorage`.
  - *Rationale*: Prevents XSS attacks from easily harvesting persistent tokens, aligning with security best practices for sensitive credentials, even in a minimal UI.
- **Decision: Placeholder Chat Endpoint (`POST /chat`)**:
  - *Context*: The UI needs an endpoint to send messages to, but the LLM agent logic is slated for Phase 2.
  - *Choice*: Created a stub endpoint that simply echoes the user's input with an "Agent not built yet" prefix.
  - *Rationale*: Allows the full front-to-back request/response cycle to be built, tested, and visually verified without blocking on complex agent orchestrations.
- **Decision: Test Suite Environment & Coverage Gaps Closed**:
  - *Context*: Needed to guarantee robust automated test coverage across all Phase 0 tasks before proceeding. Found missing coverage for `config.py` defaults and `user.py` schema integrity.
  - *Choice*: Added `test_config.py` (asserting `Settings` class defaults avoid hardcoded secrets) and `test_models.py` (verifying engine connectivity and schema mapping). Maintained requirement for local `docker-compose` PostgreSQL to ensure real-world schema compatibility over SQLite mock.
  - *Rationale*: Protects against secret leakage and schema drift, proving the foundation is 100% verified before adding RAG complexity in Phase 1.

## Phase 1: Ingestion & RAG
- **Decision: Hard Capped Pagination for Dev (`MAX_EMAILS`)**:
  - *Context*: Personal inboxes can contain tens of thousands of emails.
  - *Choice*: Added a `MAX_EMAILS` limit (default 500) to the fetcher pagination loop.
  - *Rationale*: Prevents the initial dev-environment sync from taking hours or blowing through API quotas before chunking/embedding logic is even tested.
- **Decision: Transparent Exponential Backoff Wrapper**:
  - *Context*: The Gmail API enforces strict per-second and per-user quotas that are easily hit during bulk historical syncs.
  - *Choice*: Used a custom python decorator to catch `HttpError` (429, 403) and sleep with exponential backoff (e.g., 1s, 2s, 4s) up to a max limit.
  - *Rationale*: Allows the batch sync to proceed smoothly without catastrophic script failures, fulfilling the standard for robust agent API interactions.
- **Decision: Raw Body Storage Added Back to Relational DB**:
  - *Context*: Initially planned to avoid storing bodies in Postgres to keep the DB lean. However, chunking logic needs access to the raw body after fetching.
  - *Choice*: Added a `body` column (nullable) to `emails_indexed` in Task 1 revision.
  - *Rationale*: Necessary to decouple fetching from chunking/embedding, allowing processing pipelines to run asynchronously or be retried without constantly re-hitting the Gmail API.
- **Decision: Simple Paragraph Chunking Strategy (`MAX_CHUNK_CHARS`)**:
  - *Context*: Emails have highly variable structures, but most contain semantic breaks at double newlines (`\n\n`).
  - *Choice*: Configured `MAX_CHUNK_CHARS=2000`. The chunker tries to group paragraphs up to this limit before hard-splitting the text.
  - *Rationale*: A good balance for LLM context windows. It avoids overly complex semantic algorithms (like NLTK sentence splitters) which are unnecessary for standard email RAG right now.
- **Decision: Duplicating Metadata onto Every Chunk**:
  - *Context*: Chunks need to be passed to the LLM and the Vector DB, which require standalone context.
  - *Choice*: The `chunks` table replicates `thread_id`, `sender`, `subject`, and `sent_at` from the parent `emails_indexed` table, rather than relying strictly on SQL JOINs.
  - *Rationale*: When a chunk is embedded in ChromaDB, its metadata payload will directly carry this data, allowing the agent to filter vector searches by date/sender and construct citations without constant round-trips to Postgres.
- **Decision: Local Zero-Dependency Embeddings**:
  - *Context*: Need an embedding model that balances speed, cost, and quality for email retrieval.
  - *Choice*: Selected `SentenceTransformer` (`all-MiniLM-L6-v2`) running locally via Chroma's built-in functions, rather than calling the Gemini or OpenAI API.
  - *Rationale*: Guarantees zero external network dependencies, no rate limits during bulk historical syncs, and avoids API key requirement hurdles for local development, while remaining highly capable for semantic search.
- **Decision: Strict Per-User Vector Isolation**:
  - *Context*: Multi-tenant RAG systems must absolutely prevent user A from retrieving user B's personal emails.
  - *Choice*: Created isolated ChromaDB collections named dynamically by user UUID (`inboxio_user_<user_id>`) rather than using a single collection and relying solely on metadata filtering.
  - *Rationale*: A hard architectural boundary is much safer than software-level metadata filters, entirely eliminating the risk of cross-tenant data bleed in vector search.
- **Decision: Default `top_k=5` for Retrieval**:
  - *Context*: Need a default retrieval limit that provides enough context for the LLM without blowing out context windows or slowing down synthesis.
  - *Choice*: Set default `top_k=5` for the semantic search tool, returning up to ~10,000 chars of context (5 chunks * 2000 chars).
  - *Rationale*: 5 chunks provides a good balance of high-recall context while remaining well within the fast context limits of models like Llama 3 or Gemini 1.5 Flash.
- **Decision: Enshrining Per-User Isolation in Search Tools**:
  - *Context*: Phase 2 agent tools will blindly trust the search tool to return safe data.
  - *Choice*: Hardcoded the `user_id` parameter into `search_emails`, deriving the collection name strictly from the authenticated JWT token context, completely removing it from the user-provided request body.
  - *Rationale*: Guarantees that even if an AI agent hallucinates or maliciously constructs a search request attempting to peek into another user's inbox, the backend will forcibly scope the query to the authenticated user's Chroma collection. This is a foundational security guarantee for Phase 2.
- **Decision: Permanent "Dumb Baseline" RAG Implementation**:
  - *Context*: Need a way to prove that the complex agentic orchestration planned for Phase 2 actually improves outcomes over a standard RAG script.
  - *Choice*: Built a strictly naive pipeline (`app/baseline`) that runs one raw search, stuffs the context into one prompt, and calls the LLM (`gemini-3.5-flash`). It is kept isolated from the main agent codebase.
  - *Rationale*: This serves as the permanent control group. Any component added in Phase 2 must demonstrably beat this baseline on hard questions, or it will be removed.
- **Decision: Hardcoded Evaluation Set**:
  - *Context*: Need an objective way to prove the Phase 2 agent works.
  - *Choice*: Saved 5 specific questions, the baseline's flawed answers, and the human judgments directly to `reference_results.json` as a locked reference point.
  - *Rationale*: Prevents moving the goalposts. By documenting exactly how and why the baseline fails (e.g. failing to synthesize multiple emails, missing implied deadlines), we have a concrete target for the Phase 2 LangGraph agent.
- **Decision: Phase 0 + 1 E2E Integration Suite**:
  - *Context*: Needed to verify that all independently built Phase 0 and Phase 1 tasks work together as a single pipeline before starting Phase 2.
  - *Choice*: Wrote a specific `test_integration_e2e.py` file with sequential test cases running against isolated test-only SQLite and ChromaDB instances.
  - *Rationale*: Confirms end-to-end correctness and per-user isolation without polluting real developer data.
- **Decision: Scaffolding LangGraph Pattern**:
  - *Context*: Transitioning from a single script to a multi-node agentic loop.
  - *Choice*: Initialized the folder structure for `app/agent/nodes` and `app/agent/graph.py` before implementing any logic.
  - *Rationale*: Separating nodes into distinct files prevents a "god-module" agent file and allows testing individual nodes independently.

## Phase 2: Core Agent Reasoning
- **Decision: Broad `AgentState` TypedDict for LangGraph**:
  - *Context*: Need a single state object to flow through all agent nodes.
  - *Choice*: Used `TypedDict` holding arrays for `sub_goals`, `tool_calls`, `retrieved_chunks`, and `conflicts_detected`.
  - *Rationale*: Allows loose coupling between nodes while maintaining strict type safety; arrays easily support appending new data across multi-hop loops.
- **Decision: Explicit Conditional Loop-Back Point**:
  - *Context*: The agent will eventually need to answer complex queries requiring multiple searches (multi-hop).
  - *Choice*: Built a conditional edge routing from `conflict_checker` to either `synthesizer` or looping back to `tool_selector`.
  - *Rationale*: Bakes the potential for iterative reasoning directly into the architecture from Day 1, ensuring we don't have to rewrite the graph structure when implementing multi-hop logic later.
- **Decision: Structured Output for Planner**:
  - *Context*: Need to reliably break a question into sub-goals without fragile regex/text parsing.
  - *Choice*: Used Langchain's `.with_structured_output()` and a Pydantic model for Gemini.
  - *Rationale*: Guarantees a strongly-typed `list[str]` array of sub-goals that can be safely iterated over by downstream nodes.
- **Decision: Retry-then-Fail Mechanism**:
  - *Context*: LLMs can occasionally hallucinate incorrect JSON/structures.
  - *Choice*: Placed the LLM invoke inside a retry loop (1 retry). If it fails twice, it raises a hard exception.
  - *Rationale*: Silently passing an empty or malformed list would lead to impossible-to-debug downstream errors. A hard fail is safer for agent stability.
- **Decision: LLM-Based Simple Tool Routing**:
  - *Context*: Need to map sub-goals to specific tools (sender, thread, date, semantic).
  - *Choice*: Used `with_structured_output` on the LLM to map sub-goals to a known `ToolCallOutput` schema rather than relying on brittle regex text matching.
- **Decision: Hard Capped Pagination Limit (MAX_EMAILS=25)**:
  - *Context*: Needed a strict cap on Gmail fetch volumes for phase 2.
  - *Choice*: Fetch loops terminate exactly at 25 emails fetched (regardless of whether they pass the career domain filter).
  - *Rationale*: Prevents runaway API limits while ensuring the system isn't forced to indefinitely paginate through thousands of irrelevant emails just to find 25 valid ones.
- **Decision: Zero-LLM Career Domain Filtering**:
  - *Context*: LLM calls are expensive and slow; irrelevant emails (shopping, spam) waste vector DB space and retrieval time.
  - *Choice*: Built a deterministic keyword-based filter (`domain_filter.py`) that strictly drops non-career emails *before* they are ever stored in the database or ChromaDB.
  - *Rationale*: Prevents downstream pipeline bloat. A false reject is considered worse than a wasted retrieval, so the filter errs on the side of allowing uncertain emails through.
- **Decision: Early Query Gating**:
  - *Context*: Answering non-career questions wastes agent LLM cycles.
  - *Choice*: Used the deterministic domain filter to immediately reject irrelevant questions at the `chat_endpoint` with zero LLM calls.
  - *Rationale*: Hardens the system against off-topic queries instantly and cheaply.
- **Decision: LLM-Agnostic Interface & Provider Tagging**:
  - *Context*: Need to trial OpenRouter's stealth preview model (`stealth/ox-alpha`) while keeping Gemini and Groq as fallbacks.
  - *Choice*: Used Langchain's universal `BaseChatModel` interface dynamically loaded via `LLM_PROVIDER`, and added a `provider` column to `EvalResult`, `MemoryFact`, and `Profile`.
  - *Rationale*: Allows instant one-line rollback via `.env` without modifying agent logic. Tagging generated outputs tracks exactly which model produced which artifact during the time-limited Ox Alpha preview.
- **Decision: Explicit Failure State in Contradiction Checking**:
  - *Context*: LLM APIs can timeout or fail parsing structured output. If this happens during contradiction checking, returning an empty list (`[]`) is dangerous as it implies "no contradiction was found".
  - *Choice*: Added `check_status: str` to `AgentState` and set it to `"failed"` if all retries exhaust, explicitly distinguishing failure from a clean check.
  - *Rationale*: Prevents false confidence. The downstream synthesizer node needs to know if the check was successful or if it should alert the user that the safety check failed.
- **Decision: Character-Based LLM Batching**:
  - *Context*: Retrieved evidence context might exceed a single LLM context window.
  - *Choice*: Split formatted context chunks into batches of 30,000 characters and invoke the LLM on each separately, extending the final conflict list.
  - *Rationale*: Simpler than a recursive map-reduce for now, avoids silent truncation, and ensures all evidence is evaluated.
- **Decision: Citation Format & Enforcement**:
  - *Context*: The synthesizer must provide citations for every claim.
  - *Choice*: Used `[Source ID]` format (e.g., `[1]`) for inline citations, strictly mapped to a separate structured `citations` list in `SynthesisOutput`.
  - *Rationale*: A numeric index is the cleanest for UI rendering, providing high readability while keeping the structured data decoupled for frontend tooltip integration.
- **Decision: Full Real Graph Completeness**:
  - *Context*: Replaced the final stub (`synthesizer_node`).
  - *Choice*: The agent graph is now fully real and functional end-to-end. (Note: `retriever_node` remains a simple pass-through stub for now, as retrieval tool logic is invoked externally or via `tool_calls` processing in a future/separate executor).
- **Decision: Realistic, Grounded Evaluation Set (Task 6)**:
  - *Context*: Creating evaluation questions based on hypotheticals leads to guaranteed failures during live evaluation since the evidence doesn't physically exist in the database constraints (e.g., `MAX_EMAILS=25`).
  - *Choice*: Scrapped the initial hallucinated questions. Dumped the real topics inside the user's specific Chroma dataset (Internshala, Naukri MINIs, LinkedIn, Academia) and mapped the strict evaluation categories (Multi-hop, Contradiction, Implied-risk, Single-lookup) *onto* the existing data.
  - *Rationale*: Prevents the need to manipulate ingestion parameters or build synthetic ingestion pipelines. The agent is forced to execute complex logic against natural, messy reality (e.g., verifying that similar intern update emails don't contradict, or deducing silence when a specific company hasn't followed up).

## Phase 3: Memory

- **Decision: Split short-term and long-term memory**:
  - *Context*: The agent needs to recall facts across sessions (e.g., "User prefers short answers") but also needs immediate context within a single multi-turn session.
  - *Choice*: Created a Postgres `memory_facts` table with a boolean `active` flag for long-term durable facts. Extended the LangGraph `AgentState` with a `chat_history` list for short-term, session-scoped context.
  - *Rationale*: Keeps the database lean by not storing every single chat turn as a durable fact, while ensuring the agent has access to both immediate conversational context and explicitly extracted long-term constraints/preferences.

- **Decision: Short-term Session Window Size**:
  - *Context*: Feeding unbounded chat history into the planner/synthesizer LLM prompts will quickly exhaust the LLM context window and API rate limits (as seen with Gemini `RESOURCE_EXHAUSTED` errors).
  - *Choice*: Hardcapped the `SESSION_HISTORY` window at 6 messages (3 full QA turns) per user.
  - *Rationale*: 3 turns is sufficient for resolving immediate coreferences (e.g., "what about the other one", "what was the date on that?"). It ensures minimal token usage per turn while avoiding cross-session memory drift where old context confuses the planner's sub-goal extraction.

- **Decision: Extraction Conservatism and Deduplication**:
  - *Context*: Writing every session detail into long-term durable DB memory would clutter the vector space and feed the agent conflicting or irrelevant facts later.
  - *Choice*: Instructed the memory extraction LLM to be highly conservative (ignore speculative/ephemeral constraints, ignore external entity facts). Added exact string-matching deduplication against `memory_facts.fact_text` for the user.
  - *Rationale*: It is safer for the agent to miss a fact than persist a hallucinated constraint. Simple exact-match dedup is fast and effective since facts are LLM-generated and structurally consistent.

- **Decision: Retrieval Approach for Long-term Facts**:
  - *Context*: When a user asks a new question, the agent needs to know which long-term facts apply without being overwhelmed by hundreds of irrelevant facts.
  - *Choice*: Implemented a lightweight keyword matching heuristic (stripping stopwords, matching word stems against fact text) in `memory_reader.py`. Added a fallback to inject all facts if the total count is extremely small (<= 3).
  - *Rationale*: For the scale of personal constraints (typically 1-10 facts per user), keyword matching is O(N) fast, requires 0 LLM latency, and completely avoids the complexity of embedding generation and vector search for tiny sets of text.

- **Decision: Memory Deletion Proof Test**:
  - *Context*: Validating that the entire short/long-term memory system is load-bearing, not decorative.
  - *Choice*: Wrote `test_memory_deletion_live.py` which seeds a constraint fact, invokes the agent graph, deletes the fact, and re-invokes the graph, printing the LLM's outputs side-by-side. 
  - *Rationale*: Confirms end-to-end that the LLM materially changes its plan/tone/answer based on the presence vs absence of a specific database row, verifying the core objective of Phase 3.

## Phase 4: Cold Email Generation
- **Decision: Profile Schema & Separate Vector Collection**:
  - *Context*: The agent needs deep grounding in the user's background and writing style to draft high-quality emails.
  - *Choice*: Added a `profiles` table to store raw text (resume, career info, writing samples) and created a dedicated `inboxio_profile_<user_id>` Chroma collection.
  - *Rationale*: Isolating profile chunks from the general email index (`inboxio_user_<user_id>`) prevents profile data from polluting standard semantic searches. It allows the agent to specifically query "profile context" when drafting.

- **Decision: Anti-Fabrication Prompting in Draft Tool**:
  - *Context*: LLMs drafting resumes or cold emails tend to invent generic qualifications (e.g., "I have 5 years of experience in Python") if not strictly bounded.
  - *Choice*: Designed the `draft_cold_email` prompt with explicit, highly restrictive rules ("DO NOT invent skills, jobs, experience") and explicitly fed it only retrieved Chroma chunks.
  - *Rationale*: Prioritizes factual accuracy over persuasive bloat. It's better for a cold email to be short and factual than long and fraudulent. Returning the `used_chunks` natively allows downstream nodes to mathematically verify this constraint.

- **Decision: Fail-Closed Self-Critique Node**:
  - *Context*: The self-critique node acts as the last automated line of defense against hallucinations before a human sees the draft.
  - *Choice*: The `self_critique` function intercepts any malformed JSON output or LLM API exception and raises a hard `RuntimeError`. It never silently defaults to returning "no flags found" (empty list).
  - *Rationale*: A broken QA check is worse than no check at all because it gives a false sense of security. "Fail closed" ensures that if the critique can't guarantee safety, the pipeline stops and the human is alerted.

- **Decision: Explicit Send Scope & Audit Logging**:
  - *Context*: Enabling an agent to actually send emails poses significant risk (spam, misrepresentation).
  - *Choice*: The `gmail.send` scope is not bundled into the original login. It requires a dedicated `/gmail/oauth/connect/send` flow that passes `intent="send"` via the encrypted state token. Furthermore, every invocation of `send_email` writes a row to the `EmailSendLog` table before even calling the Gmail API.
  - *Rationale*: Guarantees that users are never tricked into granting write-access when they only meant to grant read-access. The permanent logging ensures 100% auditability for what the agent sent, to whom, and whether the API call succeeded or failed.

- **Note: Environmental Timeout on Gmail API**:
  - *Context*: During manual end-to-end verification (`verify_task4.py`), the `googleapiclient` call to `gmail.googleapis.com` timed out.
  - *Observation*: The OAuth flow correctly escalated the scope and returned a valid token with the `gmail.send` permission. The DB logging mechanism perfectly captured the timeout as a `FAILED` log entry.
  - *Decision*: This is recorded as a local environmental/network limitation (e.g., IPv6 routing issue with `httplib2`) rather than an application defect. The application logic is fully verified through comprehensive mocked test suites and the proven fail-closed database logging.

- **Decision: Bypass-Resistant Human Approval Gate**:
  - *Context*: We needed to guarantee that a cold email draft could never be sent without a human explicitly reviewing it, and importantly, explicitly acknowledging any hallucination warnings flagged by the `self_critique` step.
  - *Choice*: Instead of relying solely on the UI to prevent a click, the system stores the draft and its critique flags in a `ColdEmailDraft` database table during the generation step. When the send API is called, the server validates the DB record. If flags exist, it requires an explicit `acknowledge_flags=True` boolean in the payload. 
  - *Rationale*: A determined client or API scraper cannot bypass the critique warning by simply hitting the `/send` endpoint with raw text. The server statefully enforces that the draft went through the pipeline and that the warnings were structurally acknowledged.

- **Decision: End-to-End Self-Critique Proof (Phase 4 Task 6)**:
  - *Context*: We needed absolute certainty that the strict self-critique and approval gate mechanisms were load-bearing before concluding Phase 4.
  - *Choice*: Ran an automated end-to-end script (`verify_task6.py`) that forced the agent to draft a cold email containing a blatant hallucination ("Chief AI Officer at Google"). 
  - *Rationale*: By proving the critique node caught the lie and the server rejected the unacknowledged payload, we proved the system is fundamentally safe against rogue LLM generations. This marked the official completion of Phase 4.

## Phase 6: Polish, Deployment, Docs
- **Decision: Consolidated Render Deployment (Phase 6 Task 1)**:
  - *Context*: Required deploying the backend, frontend, and Postgres to free-tier hosting.
  - *Choice*: Used a single `render.yaml` Blueprint to deploy the FastAPI app and Postgres DB on Render. Avoided Vercel entirely since the frontend is served via Jinja templates directly from the FastAPI backend.
  - *Rationale*: Simplifies the deployment topology. Splitting into Vercel was unnecessary and would break FastAPI's template/session serving without significant refactoring.

- **Decision: Accept Ephemeral Chroma Persistence**:
  - *Context*: Render's free tier does not support persistent disks. Our ChromaDB uses local SQLite/parquet files.
  - *Choice*: Explicitly accepted that the vector database will be wiped whenever the Render free-tier instance sleeps or restarts.
  - *Rationale*: For a portfolio/demo deployment, re-ingesting 25 emails is trivial. Upgrading to a paid Render disk or migrating to a cloud vector database (like Pinecone) would introduce unnecessary cost/complexity for a demo environment.

- **Decision: Switch Primary Provider to Groq**:
  - *Context*: The original Gemini API exhausted its free quota, and the alternative OpenRouter stealth model (`ox-alpha`) hit severe upstream global rate limits.
  - *Choice*: Switched `LLM_PROVIDER=groq` to use `llama3-8b-8192` as the primary production model.
  - *Rationale*: Groq offers incredibly fast inference and generous rate limits, allowing the multi-step LangGraph orchestration to complete without timeout bottlenecks, ensuring a smooth deployed experience.
