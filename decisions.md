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
