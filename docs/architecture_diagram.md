# StreamAssist Multi-Agent Architecture

## Overview

StreamAssist is a production-oriented multi-agent customer support platform built using FastAPI, Streamlit, PostgreSQL (Pagila), MCP-style tool abstractions, and OpenAI-compatible LLMs.

The system uses LLM-powered intent classification to route customer requests to specialized support agents. Each agent can invoke approved tools through a shared MCP Tool Layer, retrieve grounded information from PostgreSQL, and return structured responses that are validated by a Guardrail Reviewer before being sent back to the user.

The platform supports both standard request/response interactions and real-time Server-Sent Events (SSE) streaming.

---

## High-Level Architecture

```text
User
 │
 ▼
Streamlit UI
(Standard + SSE Streaming)
 │
 ▼
FastAPI Gateway
(/respond, /stream)
 │
 ▼
TriageAgent
(Intent Classification + Routing)
 │
 ├── CatalogAgent
 ├── SubscriptionAgent
 ├── RentalHistoryAgent
 ├── KnowledgeAgent
 └── HandoffAgent
        │
        ▼
MCP Tool Layer
 │
 ├── search_film_catalog()
 ├── get_customer_streaming_subscription()
 ├── get_customer_rental_history()
 ├── search_knowledge_base()
 └── create_handoff_ticket()
        │
        ▼
PostgreSQL (Pagila)
        │
        ▼
Guardrail Reviewer
        │
        ▼
Structured Response
(JSON / SSE Events)
```

---

## Agent Responsibilities

### TriageAgent

Responsible for:

* Intent classification
* Confidence scoring
* Dynamic agent selection
* Routing customer requests
* Fallback handling

---

### CatalogAgent

Handles:

* Film catalog searches
* Inventory lookups
* Movie availability requests

Tool access:

```text
search_film_catalog()
```

---

### SubscriptionAgent

Handles:

* Subscription status
* Plan information
* Billing-related support

Tool access:

```text
get_customer_streaming_subscription()
```

---

### RentalHistoryAgent

Handles:

* Rental history requests
* Recently rented movies
* Rental activity summaries

Tool access:

```text
get_customer_rental_history()
```

---

### KnowledgeAgent

Handles:

* FAQ retrieval
* Policy questions
* Grounded support responses

Tool access:

```text
search_knowledge_base()
```

---

### HandoffAgent

Handles:

* Escalation workflows
* Human support requests
* Ticket creation

Tool access:

```text
create_handoff_ticket()
```

---

## MCP Tool Layer

The MCP Tool Layer provides a standardized interface between agents and backend resources.

Benefits:

* Shared tool contracts
* Agent independence
* Easier testing
* Future MCP server compatibility
* Clear separation of orchestration and execution

Current tools:

| Tool                                  | Purpose                  |
| ------------------------------------- | ------------------------ |
| search_film_catalog()                 | Film lookup              |
| get_customer_streaming_subscription() | Subscription retrieval   |
| get_customer_rental_history()         | Rental history retrieval |
| search_knowledge_base()               | Knowledge retrieval      |
| create_handoff_ticket()               | Escalation workflow      |

---

## Guardrail Layer

Every generated response passes through a Guardrail Reviewer before being returned.

Validation checks include:

* Prompt injection detection
* Unsafe action prevention
* Grounding verification
* Response structure validation
* PII protection
* Hallucination prevention

Guardrail output includes:

```json
{
  "triggered": false,
  "checks_passed": [
    "message_pattern_check",
    "answer_pattern_check",
    "llm_safety_review"
  ]
}
```

---

## Observability

The system includes a dedicated observability layer for monitoring and debugging.

Captured metrics:

* Request latency
* Agent selection
* Tool execution
* Retry attempts
* Token usage
* Model information
* Error tracking
* Structured application logs

Optional integrations:

* Langfuse tracing
* OpenTelemetry
* External monitoring systems

---

## Reliability Features

Implemented features:

* Multi-agent orchestration
* Intent-based routing
* Confidence scoring
* Structured JSON responses
* SSE streaming support
* Retry handling
* Timeout protection
* Tool isolation
* Human escalation workflow
* Guardrail validation
* Response grounding
* Automated testing

---

## Security Features

The system protects against:

* Prompt injection attacks
* Unsafe account mutations
* Ungrounded responses
* Hallucinated ticket references
* Customer data exposure
* Invalid tool execution

---

## Response Formats

### Standard Response

```json
{
  "intent": "check_subscription_status",
  "selected_agent": "SubscriptionAgent",
  "confidence": 0.90,
  "answer": "...",
  "tools_used": [],
  "guardrail_result": {}
}
```

### Streaming Response

Server-Sent Events (SSE):

```text
event: status
event: metadata
event: token
event: final
```

---

## Testing

Automated pytest coverage validates:

* Agent routing
* Intent classification
* Tool execution
* Rental history workflows
* Subscription workflows
* Human handoff workflows
* Prompt injection defense
* Guardrail validation
* PII detection
* Structured response contracts

Current status:

```text
16 / 16 tests passing
```

---

## Technology Stack

* Python 3.12
* FastAPI
* Streamlit
* PostgreSQL (Pagila)
* Pydantic
* MCP-style Tool Layer
* Groq / OpenAI-compatible LLM APIs
* Langfuse (optional)
* Docker Compose
* Pytest
* Server-Sent Events (SSE)

---

## Architecture Diagram

Refer to:

```text
docs/architecture.png
docs/architecture.drawio
```

for the complete visual system architecture.
