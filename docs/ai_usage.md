# AI Usage Notes

## Overview

AI-assisted development was used throughout this project to accelerate implementation, generate boilerplate, improve documentation quality, and assist with testing and validation.

All generated code, prompts, SQL queries, architectural decisions, and production enhancements were manually reviewed, understood, tested, and adjusted before inclusion.

The final system design, safety controls, reliability mechanisms, observability features, and evaluation framework were intentionally selected and validated rather than accepted blindly.

---

# AI Tools Used

## Claude

Primary usage:

* Initial project scaffolding
* Agent implementation assistance
* Tool implementation assistance
* Test generation
* Documentation drafting
* Architecture documentation

## ChatGPT

Used for:

* Design reviews
* Guardrail improvements
* Reliability enhancements
* Observability improvements
* Langfuse integration review
* MCP server validation
* Evaluation framework refinement
* Streaming endpoint implementation review
* Documentation refinement

---

# AI-Assisted Areas

## Project Structure

AI was used to accelerate creation of:

* FastAPI application structure
* Agent organization
* Tool organization
* Database layer layout
* Documentation structure
* Evaluation framework structure

---

## Typed Data Contracts

AI assisted with:

* Pydantic request schemas
* Pydantic response schemas
* Tool input/output contracts
* Structured JSON response design

All schemas were manually reviewed and validated against application requirements.

---

## Database Layer

AI assisted with:

* SQLAlchemy async patterns
* Session management
* Migration scaffolding
* Repository organization

All SQL queries were manually reviewed against the Pagila schema before acceptance.

---

## Guardrails

AI assisted with:

* Prompt injection detection patterns
* Safety review prompt creation
* Structured safety evaluation outputs

Additional validation logic and grounding checks were manually refined during implementation.

---

## Testing

AI assisted with:

* Pytest boilerplate
* AsyncMock patterns
* Evaluation scenario generation
* Regression testing structure

All tests were executed and validated manually.

Current validation results:

```text
Pytest:
16 / 16 tests passing

Eval Runner:
10 / 10 scenarios passing
```

---

# Production-Oriented Enhancements

The following enhancements were added after the initial implementation phase.

## Observability

Added:

* Request latency logging
* LLM latency logging
* Prompt token tracking
* Completion token tracking
* Total token tracking
* Retry attempt logging

Purpose:

* Cost monitoring
* Performance monitoring
* Troubleshooting support
* Operational visibility

---

## Langfuse Observability

Optional Langfuse tracing was added to monitor LLM interactions.

When enabled, Langfuse captures:

* LLM requests
* LLM responses
* Model metadata
* Token usage
* Latency metrics
* Generation traces

Configuration is controlled through environment variables:

```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

The application continues to function normally if Langfuse is disabled or credentials are unavailable.

This allows local development, CI execution, and assignment review without requiring external dependencies.

---

## Reliability

Added:

### Retry Handling

* Exponential backoff retry logic
* Configurable retry count
* Retry logging

Purpose:

* Temporary provider failures
* Network instability
* Rate limiting resilience

### Timeout Protection

* Configurable LLM request timeout
* Graceful failure handling

Purpose:

* Prevent hanging requests
* Improve system reliability

### JSON Repair

* Automatic recovery from malformed JSON responses
* Structured fallback behavior

Purpose:

* Increase routing reliability
* Reduce failures caused by imperfect LLM outputs

---

## Streaming Support

Added:

### Server-Sent Events Endpoint

```text
POST /agent/respond/stream
```

Features:

* Status events
* Metadata events
* Token streaming
* Final structured response event

Purpose:

* Improved user experience
* Demonstration of production GenAI interaction patterns
* Faster perceived response times

---

## MCP Integration

Added:

### Local MCP Server

```text
python mcp_server.py
```

Capabilities:

* MCP initialize support
* Tool discovery (`tools/list`)
* Tool execution (`tools/call`)
* PostgreSQL-backed tool access

Verified tools:

* search_film_catalog
* get_customer_streaming_subscription
* get_customer_rental_history

Purpose:

* Demonstrate MCP compatibility
* Future agent interoperability
* Tool portability

---

## Evaluation Framework

The project includes a lightweight evaluation framework.

Location:

```text
evals/run_evals.py
```

Capabilities:

* Agent routing validation
* Tool invocation validation
* Safety validation
* Grounding validation
* Regression testing

Results are exported to:

```text
evals/eval_results.json
```

Current status:

```text
10 / 10 evaluation scenarios passing
```

---

# Manual Review Activities

The following areas received explicit manual review.

## Database Queries

Reviewed:

* Join paths
* Foreign key relationships
* Column selections
* Query performance assumptions

---

## Guardrails

Reviewed:

* False positive behavior
* Prompt injection detection
* Grounding verification
* Human escalation logic

---

## Triage Agent

Reviewed:

* Intent classification consistency
* Confidence handling
* Fallback behavior
* JSON output reliability

---

## Human Handoff Workflow

Reviewed:

* Ticket creation behavior
* Ticket grounding validation
* Hallucination prevention
* Escalation paths

---

## MCP Server

Reviewed:

* JSON-RPC message handling
* Tool registration
* Tool execution behavior
* Windows compatibility fixes
* End-to-end MCP validation

---

## Langfuse Integration

Reviewed:

* OpenAI-compatible wrapper integration
* Environment-based enable/disable behavior
* Token tracking
* Trace generation
* Failure handling when tracing is disabled

---

## Evaluation Results

Reviewed:

* Pass/fail criteria
* Agent selection correctness
* Tool selection correctness
* Safety behavior correctness
* Grounding behavior correctness

---

# Development Philosophy

AI was treated as an accelerator rather than an authority.

Architectural decisions remained driven by software engineering principles:

* Separation of concerns
* Typed contracts
* Explicit safety layers
* Observability
* Reliability
* Testability
* Reproducibility

The final architecture would remain fundamentally the same without AI assistance; AI primarily accelerated implementation, documentation, and boilerplate generation.

---

# Code Review Confidence

All submitted code has been read, executed, tested, and reviewed.

No production-facing component was included without validation.

Final project status:

```text
16 / 16 tests passing
10 / 10 eval scenarios passing

Streaming endpoint operational
MCP server operational
Langfuse tracing operational

Retry handling operational
Timeout protection operational
JSON repair operational

Token usage monitoring operational
Latency monitoring operational
```
