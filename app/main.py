"""
StreamAssist AI Support Agent - Main FastAPI Application
"""
from dotenv import load_dotenv
load_dotenv()

import json
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.models.schemas import AgentRequest, AgentResponse
from app.agents.triage_agent import TriageAgent
from app.agents.catalog_agent import CatalogAgent
from app.agents.subscription_agent import SubscriptionAgent
from app.agents.rental_history_agent import RentalHistoryAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.handoff_agent import HumanHandoffAgent
from app.guardrails.guardrail import GuardrailReviewer
from app.observability.logger import get_logger, log_request

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("StreamAssist starting up")
    yield
    logger.info("StreamAssist shutting down")


app = FastAPI(
    title="StreamAssist AI Support Agent",
    description="Multi-agent AI support assistant for streaming platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
triage_agent = TriageAgent()
catalog_agent = CatalogAgent()
subscription_agent = SubscriptionAgent()
rental_agent = RentalHistoryAgent()
knowledge_agent = KnowledgeAgent()
handoff_agent = HumanHandoffAgent()
guardrail = GuardrailReviewer()

AGENT_MAP = {
    "CatalogAgent": catalog_agent,
    "SubscriptionAgent": subscription_agent,
    "RentalHistoryAgent": rental_agent,
    "KnowledgeAgent": knowledge_agent,
    "HumanHandoffAgent": handoff_agent,
}


async def run_agent_pipeline(request: AgentRequest) -> AgentResponse:
    """
    Shared pipeline used by both normal JSON responses and streaming responses.

    Steps:
    1. Triage user intent
    2. Route to specialist agent
    3. Run guardrail review
    4. Return structured response
    """
    start_time = time.time()
    conversation_id = request.conversation_id or str(uuid.uuid4())

    logger.info(
        "request_received",
        extra={
            "conversation_id": conversation_id,
            "customer_id": request.customer_id,
            "message_preview": request.message[:80],
        },
    )

    try:
        # Step 1: Triage
        triage_result = await triage_agent.run(
            message=request.message,
            customer_id=request.customer_id,
            conversation_id=conversation_id,
        )

        selected_agent_name = triage_result.selected_agent
        intent = triage_result.intent
        confidence = triage_result.confidence

        # Step 2: Route to specialist agent
        specialist = AGENT_MAP.get(selected_agent_name, knowledge_agent)
        agent_result = await specialist.run(
            message=request.message,
            customer_id=request.customer_id,
            conversation_id=conversation_id,
        )

        # Step 3: Guardrail review
        guardrail_result = await guardrail.review(
            message=request.message,
            answer=agent_result.answer,
            intent=intent,
            conversation_id=conversation_id,
            grounding_context=agent_result.grounding_context,
        )

        final_answer = guardrail_result.safe_answer or agent_result.answer

        latency_ms = round((time.time() - start_time) * 1000, 2)
        log_request(
            conversation_id=conversation_id,
            intent=intent,
            selected_agent=selected_agent_name,
            latency_ms=latency_ms,
            guardrail_triggered=guardrail_result.triggered,
        )

        return AgentResponse(
            conversation_id=conversation_id,
            intent=intent,
            selected_agent=selected_agent_name,
            answer=final_answer,
            confidence=confidence,
            tools_used=agent_result.tools_used,
            citations=agent_result.citations,
            next_action=agent_result.next_action,
            guardrail_result=guardrail_result.dict(),
        )

    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(
            "request_failed",
            extra={
                "conversation_id": conversation_id,
                "error": str(e),
                "latency_ms": latency_ms,
            },
        )
        return AgentResponse(
            conversation_id=conversation_id,
            intent="error",
            selected_agent="none",
            answer="I'm sorry, something went wrong. Please try again or contact support.",
            confidence=0.0,
            tools_used=[],
            citations=[],
            next_action="retry",
            guardrail_result={"triggered": False, "reason": None, "safe_answer": None},
        )


@app.post("/agent/respond", response_model=AgentResponse)
async def agent_respond(request: AgentRequest):
    return await run_agent_pipeline(request)


@app.post("/agent/respond/stream")
async def agent_respond_stream(request: AgentRequest):
    """
    Streaming endpoint.

    This endpoint returns Server-Sent Events (SSE). It streams status updates first,
    then streams the final answer word-by-word, followed by metadata.

    This keeps the existing /agent/respond endpoint stable while demonstrating
    streaming response support for GenAI-style UX.
    """

    async def event_generator():
        yield "event: status\n"
        yield 'data: {"stage": "received", "message": "Request received"}\n\n'

        yield "event: status\n"
        yield 'data: {"stage": "processing", "message": "Running triage, tools, and guardrails"}\n\n'

        response = await run_agent_pipeline(request)

        yield "event: metadata\n"
        yield f"data: {json.dumps({'conversation_id': response.conversation_id, 'intent': response.intent, 'selected_agent': response.selected_agent})}\n\n"

        for word in response.answer.split():
            yield "event: token\n"
            yield f"data: {json.dumps({'text': word + ' '})}\n\n"

        yield "event: final\n"
        yield f"data: {response.json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "StreamAssist"}