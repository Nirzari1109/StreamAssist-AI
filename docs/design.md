# StreamAssist — Architecture & Design

## Overview

StreamAssist is a production-oriented multi-agent AI support system for a streaming and rental platform.

A single API endpoint receives customer messages, routes them through an intent-classification layer, invokes specialized agents and database-backed tools, validates outputs through guardrails, and returns a structured response.

The architecture emphasizes:

* Agent specialization
* Strong tool boundaries
* Safety and grounding
* Observability
* Reliability
* Evaluation-driven validation
* Optional Langfuse tracing for LLM observability

---

# High-Level Architecture

```text
Customer Request
        │
        ▼
 FastAPI API Layer
        │
        ▼
    TriageAgent
(Intent Classification)
        │
        ├──────────── CatalogAgent
        ├──────────── SubscriptionAgent
        ├──────────── RentalHistoryAgent
        ├──────────── KnowledgeAgent
        └──────────── HumanHandoffAgent
                         │
                         ▼
                    Tool Layer
                         │
    ┌────────────────────────────────────┐
    │ PostgreSQL (Pagila)                │
    │ Local Knowledge Base               │
    │ Handoff Ticket Creation            │
    └────────────────────────────────────┘
                         │
                         ▼
                 Guardrail Reviewer
                         │
                         ▼
                Structured Response
                         │
                         ▼
                 Observability Layer
                         │
     ┌───────────────────────────────────┐
     │ Structured JSON Logs              │
     │ Token / Latency Metrics           │
     │ Optional Langfuse Traces          │
     └───────────────────────────────────┘
```

---

# Agent Architecture

```text
Customer Message
      │
      ▼
  TriageAgent
      │
      ▼
  ┌───────────────────────────────────────────────────────┐
  │                  Specialist Agents                    │
  │                                                       │
  │ CatalogAgent       → search_film_catalog              │
  │ SubscriptionAgent  → get_customer_streaming_sub       │
  │ RentalHistoryAgent → get_customer_rental_history      │
  │ KnowledgeAgent     → search_kb                        │
  │ HumanHandoffAgent  → create_handoff_ticket            │
  └───────────────────────────────────────────────────────┘
      │
      ▼
  Guardrail Reviewer
      │
      ▼
  Structured JSON Response
```

Each specialist agent owns a single business capability and only interacts with tools relevant to that capability.

This design minimizes prompt complexity and improves routing transparency.

---

# Routing Logic

## Step 1 — Intent Classification

TriageAgent sends the user message to an LLM with a strict JSON response contract.

Expected output:

```json
{
  "intent": "...",
  "selected_agent": "...",
  "confidence": 0.95,
  "reason": "..."
}
```

---

## Step 2 — Agent Selection

Messages are routed to the selected specialist agent.

Fallback behavior:

* Confidence below threshold
* Invalid JSON response
* Unknown agent selection

All fallback paths route to KnowledgeAgent.

---

## Step 3 — Tool Execution

The selected agent invokes one or more tools.

Tools are responsible for:

* Database access
* Knowledge retrieval
* Ticket creation

Agents do not directly access infrastructure resources.

---

## Step 4 — Guardrail Review

Responses are reviewed before returning to the user.

Safety validation includes:

* Prompt injection detection
* PII protection
* Grounding validation
* Hallucination detection

---

# Tool Boundaries & MCP Readiness

Every tool provides:

* Name
* Description
* Input schema
* Output schema
* Authentication requirements
* Ownership boundary

Benefits:

* Consistent interfaces
* Easier testing
* MCP compatibility
* Future agent interoperability

The project includes a local MCP server exposing PostgreSQL-backed tools through JSON-RPC.

The MCP server supports:

* initialize
* tools/list
* tools/call

Verified tools:

* search_film_catalog
* get_customer_streaming_subscription
* get_customer_rental_history

---

# Database Layer

## PostgreSQL

Pagila sample database with custom migrations:

### Migration 001

```text
film.streaming_available BOOLEAN
```

### Migration 002

```text
streaming_subscription
```

with:

* Foreign key to customer
* Seed subscription data

---

## Data Access

* Async SQLAlchemy
* asyncpg driver
* Parameterized SQL queries
* Connection pooling

Benefits:

* SQL injection protection
* Predictable query behavior
* Clear ownership boundaries

---

# Guardrails

The system uses a two-stage guardrail architecture.

## Stage 1 — Pattern Detection

Fast regex checks for:

* Prompt injection
* Sensitive data requests
* System prompt extraction attempts
* Unsafe account modification attempts

---

## Stage 2 — LLM Safety Review

The message and generated answer are reviewed for:

* Unsupported claims
* PII exposure
* Safety concerns
* Grounding violations

Unsafe responses are replaced with safe fallback responses.

---

# Observability

StreamAssist includes both built-in structured logging and optional Langfuse tracing.

Structured JSON logs are emitted for:

## Requests

* Request start
* Request completion
* Total latency

## Tool Calls

* Tool name
* Status
* Latency
* Error information

## Routing

* Selected agent
* Intent
* Confidence

## Guardrails

* Trigger status
* Trigger reason

## LLM Calls

* Model name
* Prompt tokens
* Completion tokens
* Total tokens
* Latency
* JSON mode usage
* Retry attempt count
* Timeout configuration

---

# Langfuse Tracing

The project includes optional Langfuse integration for LLM observability.

When enabled, Langfuse traces LLM calls made through the OpenAI-compatible client.

Tracked details include:

* Model name
* Prompt and completion flow
* Token usage
* Latency
* Request metadata
* Generation-level traces

Langfuse is controlled through environment variables:

```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

If Langfuse credentials are not present, the application runs normally without tracing.

This keeps the feature optional and safe for local development, CI, and assignment review.

---

# Production Reliability Enhancements

Several production-oriented reliability features were added beyond the original assignment requirements.

## Retry Handling

LLM requests support:

* Automatic retry
* Exponential backoff
* Retry logging

Purpose:

* Temporary provider failures
* Network instability
* Rate limiting resilience

---

## Timeout Protection

LLM requests use configurable timeout values.

Benefits:

* Prevent hanging requests
* Improve service stability
* Better operational visibility

---

## JSON Repair

Malformed JSON outputs are automatically repaired before failure.

Benefits:

* Increased routing reliability
* Reduced parsing failures
* Better production robustness

---

# Streaming Support

The project includes a streaming endpoint:

```text
POST /agent/respond/stream
```

Implemented using Server-Sent Events (SSE).

Streamed events:

```text
status
metadata
token
final
```

Benefits:

* Faster perceived responsiveness
* Better GenAI user experience
* Demonstrates production-ready interaction patterns

---

# Evaluation Framework

A lightweight evaluation framework validates core system behavior.

Location:

```text
evals/run_evals.py
```

Validation includes:

* Routing correctness
* Tool selection
* Safety behavior
* Grounding behavior
* Regression testing

Current results:

```text
10 / 10 evaluation scenarios passing
```

---

# Testing Strategy

Automated tests validate:

* Triage behavior
* Catalog retrieval
* Subscription retrieval
* Rental history retrieval
* Knowledge retrieval
* Human handoff
* Prompt injection protection
* PII protection
* Guardrail behavior

Current results:

```text
16 / 16 tests passing
```

---

# Tradeoffs

| Decision                  | Rationale                                               |
| ------------------------- | ------------------------------------------------------- |
| Specialized agents        | Simpler prompts and easier debugging                    |
| Single public endpoint    | Minimal API surface area                                |
| PostgreSQL tools          | Strong grounding and deterministic retrieval            |
| Regex + LLM guardrails    | Balance of speed and coverage                           |
| Local KB                  | Simpler deployment and auditing                         |
| SSE streaming             | Lightweight real-time interaction                       |
| Eval framework            | Continuous regression validation                        |
| Langfuse optional tracing | Adds LLM observability without blocking local execution |

---

# Known Limitations

* Knowledge base is keyword-based rather than embedding-based
* No authentication layer; customer_id is trusted input
* Guardrail review introduces additional latency
* MCP transport currently uses stdio rather than HTTP/SSE
* Streaming currently emits word-level chunks rather than model-native token streams
* Langfuse tracing requires external credentials and network access

---

# UI Enhancements

A Streamlit-based frontend was added to demonstrate production-style GenAI interaction patterns.

Features include:

* Interactive chat interface
* Standard response mode
* SSE streaming mode
* Agent execution flow visualization
* MCP tool execution visibility
* Guardrail validation visibility
* Developer JSON payload inspection
* Confidence and latency reporting

The UI is intentionally separated from the FastAPI backend to maintain a clean API boundary and support independent deployment.

---

# Future Improvements

Potential production upgrades:

* Vector database retrieval
* Semantic search
* OAuth authentication
* OpenTelemetry instrumentation
* Distributed caching
* Native MCP transport
* Multi-region deployment
* Langfuse dashboards for prompt quality and regression analysis