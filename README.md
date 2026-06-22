# StreamAssist — Multi-Agent AI Support Assistant

A production-oriented multi-agent AI support system for a streaming and rental platform built with FastAPI, PostgreSQL (Pagila), OpenAI-compatible LLMs, structured guardrails, automated evaluations, streaming responses, retry handling, and production-style observability.

---

# Architecture

```text
User
 │
 ▼
FastAPI REST API
 │
 ▼
Triage Agent
(Intent Classification)
 │
 ├── Catalog Agent
 ├── Subscription Agent
 ├── Rental History Agent
 ├── Knowledge Agent
 └── Human Handoff Agent
          │
          ▼
     Tool Layer
          │
 ├── Film Catalog Search
 ├── Subscription Lookup
 ├── Rental History Lookup
 ├── Knowledge Base Search
 └── Ticket Creation
          │
          ▼
    Guardrail Reviewer
          │
          ▼
 Structured JSON Response
          │
          ▼
 Observability Layer
 (Logs, Metrics, Usage)
```

Architecture documentation:

```text
docs/architecture_diagram.md
docs/architecture_diagram.png
docs/architecture_diagram.drawio

The architecture diagram includes:
- FastAPI API Layer
- TriageAgent
- Specialist Agents
- MCP Tool Layer
- PostgreSQL (Pagila)
- Guardrail Reviewer
- Observability Layer
- SSE Streaming Response Path
```

---

# Key Features

## Multi-Agent Architecture

* Intent-based request routing
* Specialized agents with clear responsibilities
* Human escalation workflow
* Confidence-based fallback handling

## Safety & Guardrails

* Prompt injection protection
* Hallucination mitigation
* PII detection
* Unsafe account mutation blocking
* Grounding validation

## Reliability

* Retry handling with exponential backoff
* Configurable timeout protection
* JSON output repair fallback
* Graceful error handling

## Observability

* Structured JSON logging
* Request latency monitoring
* LLM latency monitoring
* Prompt token tracking
* Completion token tracking
* Total token tracking
* Retry attempt tracking

## Evaluation

* Automated evaluation framework
* 10 evaluation scenarios
* Regression testing support
* Results export to JSON

## Streaming

* Server-Sent Events (SSE) endpoint
* Token-by-token streaming responses
* Metadata and status events

---

# Quick Start

## Prerequisites

* Python 3.11+
* PostgreSQL with Pagila sample database
* OpenAI API key or OpenAI-compatible provider (Groq)

---

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 2. Set Up Pagila Database

```bash
psql -U postgres -c "CREATE DATABASE pagila;"

# Download and restore Pagila
psql -U postgres pagila < pagila-schema.sql
psql -U postgres pagila < pagila-data.sql
```

---

## 3. Configure Environment

```bash
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pagila

export OPENAI_API_KEY=your_key_here

export OPENAI_BASE_URL=https://api.groq.com/openai/v1

export LLM_MODEL=llama-3.3-70b-versatile
```

---

## 4. Run Database Migrations

```bash
alembic upgrade head
```

---

## 5. Start the Server

```bash
uvicorn app.main:app --reload
```

---

## 6. Open Swagger UI

```text
http://localhost:8000/docs
```

---

# API Endpoints

## Standard Response Endpoint

### POST /agent/respond

Request:

```json
{
  "customer_id": 1,
  "conversation_id": "conv_001",
  "message": "Is Alien available for streaming?"
}
```

Response:

```json
{
  "conversation_id": "conv_001",
  "intent": "catalog_search",
  "selected_agent": "CatalogAgent",
  "answer": "Response text...",
  "confidence": 0.95,
  "tools_used": [
    "search_film_catalog"
  ],
  "citations": [
    "ALIEN CENTER"
  ],
  "next_action": "none"
}
```

---

## Streaming Endpoint

### POST /agent/respond/stream

Provides Server-Sent Events (SSE) streaming.

Example stream:

```text
event: status
data: {"stage":"received"}

event: metadata
data: {...}

event: token
data: {"text":"Your "}

event: token
data: {"text":"subscription "}

event: final
data: {...}
```

This endpoint demonstrates production-style GenAI response streaming.

---

# Running Tests

```bash
pytest -v
```

Current Status:

```text
16 / 16 tests passing
```

---

# Running Evaluations

```bash
python evals/run_evals.py
```

Current Status:

```text
10 / 10 evaluation scenarios passing
```

Results are exported to:

```text
evals/eval_results.json
```

---

# MCP Server

```bash
python mcp_server.py
```

Exposes:

* search_film_catalog
* get_customer_streaming_subscription
* get_customer_rental_history

---

# Bonus Features Implemented

## Production Observability

* LLM token usage logging
* Prompt token tracking
* Completion token tracking
* Total token tracking
* LLM latency monitoring
* Request latency monitoring

## Reliability

* Retry handling with exponential backoff
* Timeout protection
* JSON repair fallback

## Evaluation

* Automated evaluation runner
* Regression testing support
* Evaluation result export

## Streaming

* Server-Sent Events endpoint
* Token streaming
* Metadata events
* Final structured event
* Live streaming UI support
* Agent execution trace visualization
* Real-time status updates

## Documentation

* Architecture documentation
* Design documentation
* AI usage documentation

## Langfuse Tracing

- Optional Langfuse tracing integration
- Tracks LLM calls through Langfuse OpenAI wrapper
- Captures model, latency, token usage, prompts, and completions
- Controlled through environment variables

---

# Project Structure

```text
app/
├── main.py
├── agents/
├── tools/
├── models/
├── guardrails/
├── db/
├── observability/

migrations/
kb/
evals/
tests/
docs/

mcp_server.py
docker-compose.yml
.env.example
```

---

# Scoring Areas Addressed

| Area                     | Implementation                                            |
| ------------------------ | --------------------------------------------------------- |
| Multi-agent architecture | Intent-based routing with specialist agents               |
| Routing and escalation   | Confidence fallback and human handoff                     |
| Database-backed tools    | PostgreSQL Pagila integration                             |
| Structured outputs       | Pydantic models and JSON mode                             |
| Guardrails               | Injection prevention, PII detection, grounding validation |
| Knowledge grounding      | Local knowledge base with citations                       |
| Observability            | Structured logs, token usage, latency metrics             |
| Reliability              | Retry handling, timeout protection, JSON repair           |
| Streaming                | SSE endpoint with token streaming                         |
| Evaluations              | 10 automated evaluation scenarios                         |
| Testing                  | 16 automated pytest tests                                 |
| MCP readiness            | MCP server and tool metadata support                      |

---

# Validation Results

```text
Pytest:
16 / 16 tests passing

Eval Runner:
10 / 10 scenarios passing

Streaming Endpoint:
Operational

Retry Handling:
Operational

Timeout Protection:
Operational

Token Usage Logging:
Operational

Langfuse Tracing:
Operational when LANGFUSE_ENABLED=true

```
