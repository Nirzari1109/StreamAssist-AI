# Implementation Plan

## Phase 1 — Project Scaffolding (30 min)
- [x] FastAPI app with health endpoint
- [x] Pydantic schemas for request/response contracts
- [x] SQLAlchemy async engine + session factory
- [x] Structured logging setup

## Phase 2 — Database & Migrations (30 min)
- [x] Alembic setup with async env
- [x] Migration 001: `film.streaming_available`
- [x] Migration 002: `streaming_subscription` + seed data
- [ ] **Manual step**: restore Pagila, run `alembic upgrade head`

## Phase 3 — Tools (45 min)
- [x] `search_film_catalog` with typed I/O
- [x] `get_customer_streaming_subscription`
- [x] `get_customer_rental_history`
- [x] `search_kb` (local JSON KB files)
- [x] `create_handoff_ticket` (mock)
- [x] Tool log instrumentation

## Phase 4 — Agents (60 min)
- [x] TriageAgent (LLM JSON routing)
- [x] CatalogAgent
- [x] SubscriptionAgent
- [x] RentalHistoryAgent
- [x] KnowledgeAgent
- [x] HumanHandoffAgent with blocked mutations list

## Phase 5 — Guardrails (30 min)
- [x] Regex fast-path for known patterns
- [x] LLM safety reviewer
- [x] Safe fallback response

## Phase 6 — Tests & Evals (45 min)
- [x] 13 pytest tests covering all agents + guardrails
- [x] 10 eval examples with structured pass/fail criteria
- [x] Eval runner script

## Phase 7 — MCP & Docs (30 min)
- [x] MCP server (stdio transport) for 3 Postgres tools
- [x] docs/design.md
- [x] docs/implementation_plan.md
- [x] docs/ai_usage.md
- [x] Docker Compose

## Setup Instructions

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Restore Pagila
psql -U postgres -c "CREATE DATABASE pagila;"
curl -L https://github.com/devrimgunduz/pagila/raw/master/pagila-schema.sql | psql -U postgres pagila
curl -L https://github.com/devrimgunduz/pagila/raw/master/pagila-data.sql | psql -U postgres pagila

# 3. Run migrations
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pagila \
  alembic upgrade head

# 4. Start app
uvicorn app.main:app --reload

# 5. Test
curl -X POST http://localhost:8000/agent/respond \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "conversation_id": "demo_001", "message": "Is Alien available for streaming?"}'

# 6. Run tests
pytest

# 7. Run evals (requires app running)
python evals/run_evals.py
```

## Assumptions
- Pagila database is restored before migrations run
- OpenAI API key has access to `gpt-4o-mini`
- customer_id in requests is trusted (no auth layer)

## Testing Approach
- Unit tests mock DB and LLM; no network calls required
- Evals require the full stack running locally
- Guardrail tests verify both trigger and pass cases
