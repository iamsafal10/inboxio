# System Flow
## Phase 0: Foundations & Project Scaffolding
- **Package Architecture**:
  - `app/core`: Application settings and environment configuration (`app/core/config.py`).
  - `app/models`: Domain schemas and database models.
  - `app/routers`: FastAPI endpoint controllers.
  - `app/services`: Integrations (Gmail, Vector DB, LLM orchestrators).
  - `app/main.py`: ASGI entrypoint exposing application routes and root health check (`GET /`).
- **Configuration Flow**: Centralized `Settings` loaded via `pydantic-settings` from environment / `.env`, ensuring consistent access across services and routers.
