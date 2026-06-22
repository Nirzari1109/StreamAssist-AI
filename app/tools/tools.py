"""
Tool contracts for StreamAssist agents.
Each tool has:
  - name, description, input schema, output schema
  - error handling and observability
  - MCP-ready metadata
"""
import time
import uuid
import re
from typing import Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    FilmSearchInput, FilmSearchOutput,
    SubscriptionInput, SubscriptionOutput,
    RentalHistoryInput, RentalHistoryOutput,
    KBSearchInput, KBSearchOutput,
    HandoffInput, HandoffOutput,
)
from app.observability.logger import get_logger, log_tool_call

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# MCP-READY TOOL METADATA
# ---------------------------------------------------------------------------
TOOL_REGISTRY = {
    "search_film_catalog": {
        "name": "search_film_catalog",
        "description": "Search film catalog by title or keyword. Returns title, category, rating, rental rate, and streaming availability.",
        "input_schema": FilmSearchInput.model_json_schema(),
        "output_schema": FilmSearchOutput.model_json_schema(),
        "error_behavior": "Returns empty films list with total=0 on failure. Never raises.",
        "auth_requirement": "none",
        "ownership_boundary": "read-only film catalog",
    },
    "get_customer_streaming_subscription": {
        "name": "get_customer_streaming_subscription",
        "description": "Get a customer's streaming subscription status, plan, and renewal info.",
        "input_schema": SubscriptionInput.model_json_schema(),
        "output_schema": SubscriptionOutput.model_json_schema(),
        "error_behavior": "Returns found=False when customer has no subscription. Never exposes other customers' data.",
        "auth_requirement": "customer_id must match session",
        "ownership_boundary": "read-only subscription for requesting customer",
    },
    "get_customer_rental_history": {
        "name": "get_customer_rental_history",
        "description": "Get recent rental history for a customer, including film titles and rental dates.",
        "input_schema": RentalHistoryInput.model_json_schema(),
        "output_schema": RentalHistoryOutput.model_json_schema(),
        "error_behavior": "Returns empty rentals list when no history found.",
        "auth_requirement": "customer_id must match session",
        "ownership_boundary": "read-only rental history for requesting customer",
    },
    "search_kb": {
        "name": "search_kb",
        "description": "Search the local knowledge base for support articles. Returns article content and source references.",
        "input_schema": KBSearchInput.model_json_schema(),
        "output_schema": KBSearchOutput.model_json_schema(),
        "error_behavior": "Returns found=False with empty articles when no match.",
        "auth_requirement": "none",
        "ownership_boundary": "read-only knowledge base",
    },
    "create_handoff_ticket": {
        "name": "create_handoff_ticket",
        "description": "Create a human support escalation ticket. Does NOT mutate account state.",
        "input_schema": HandoffInput.model_json_schema(),
        "output_schema": HandoffOutput.model_json_schema(),
        "error_behavior": "Returns error status in output. Never silently fails.",
        "auth_requirement": "none",
        "ownership_boundary": "write escalation ticket only",
    },
}


# ---------------------------------------------------------------------------
# TOOL IMPLEMENTATIONS
# ---------------------------------------------------------------------------

async def search_film_catalog(
    inp: FilmSearchInput,
    db: AsyncSession,
    conversation_id: str = "unknown",
) -> FilmSearchOutput:
    start = time.time()
    tool_name = "search_film_catalog"
    try:
        sql = text("""
            SELECT
                f.film_id,
                f.title,
                f.description,
                f.rating::text AS rating,
                f.rental_rate,
                f.streaming_available,
                STRING_AGG(DISTINCT c.name, ', ') AS category
            FROM film f
            LEFT JOIN film_category fc ON f.film_id = fc.film_id
            LEFT JOIN category c ON fc.category_id = c.category_id
            WHERE f.title ILIKE :query
               OR f.description ILIKE :query
               OR f.film_id IN (
                    SELECT fc2.film_id FROM film_category fc2
                    JOIN category c2 ON fc2.category_id = c2.category_id
                    WHERE c2.name ILIKE :query
               )
            GROUP BY f.film_id, f.title, f.description, f.rating, f.rental_rate, f.streaming_available
            ORDER BY f.title
            LIMIT 5
        """)
        result = await db.execute(sql, {"query": f"%{inp.query}%"})
        rows = result.mappings().all()
        films = [dict(r) for r in rows]
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "success", latency)
        return FilmSearchOutput(films=films, total=len(films))
    except Exception as e:
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "error", latency, str(e))
        logger.error(f"{tool_name} failed: {e}")
        return FilmSearchOutput(films=[], total=0)


async def get_customer_streaming_subscription(
    inp: SubscriptionInput,
    db: AsyncSession,
    conversation_id: str = "unknown",
) -> SubscriptionOutput:
    start = time.time()
    tool_name = "get_customer_streaming_subscription"
    try:
        sql = text("""
            SELECT
                id,
                customer_id,
                plan_name,
                status,
                start_date::text,
                end_date::text,
                auto_renew
            FROM streaming_subscription
            WHERE customer_id = :cid
            ORDER BY start_date DESC
            LIMIT 1
        """)
        result = await db.execute(sql, {"cid": inp.customer_id})
        row = result.mappings().first()
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "success", latency)
        if row is None:
            return SubscriptionOutput(customer_id=inp.customer_id, found=False)
        return SubscriptionOutput(
            customer_id=inp.customer_id,
            found=True,
            plan_name=row["plan_name"],
            status=row["status"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            auto_renew=row["auto_renew"],
        )
    except Exception as e:
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "error", latency, str(e))
        logger.error(f"{tool_name} failed: {e}")
        return SubscriptionOutput(customer_id=inp.customer_id, found=False, error=str(e))


async def get_customer_rental_history(
    inp: RentalHistoryInput,
    db: AsyncSession,
    conversation_id: str = "unknown",
) -> RentalHistoryOutput:
    start = time.time()
    tool_name = "get_customer_rental_history"
    try:
        sql = text("""
            SELECT
                f.title,
                r.rental_date::text,
                r.return_date::text,
                p.amount AS payment_amount
            FROM rental r
            JOIN inventory i ON r.inventory_id = i.inventory_id
            JOIN film f ON i.film_id = f.film_id
            JOIN customer c ON r.customer_id = c.customer_id
            LEFT JOIN payment p ON r.rental_id = p.rental_id
            WHERE r.customer_id = :cid
            ORDER BY r.rental_date DESC
            LIMIT :lim
        """)
        result = await db.execute(sql, {"cid": inp.customer_id, "lim": inp.limit})
        rows = result.mappings().all()
        rentals = [dict(r) for r in rows]
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "success", latency)
        return RentalHistoryOutput(customer_id=inp.customer_id, rentals=rentals, total=len(rentals))
    except Exception as e:
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "error", latency, str(e))
        logger.error(f"{tool_name} failed: {e}")
        return RentalHistoryOutput(customer_id=inp.customer_id, rentals=[], total=0)


# KB articles loaded from local files
import json
import os

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "kb")


def _load_kb() -> list[dict]:
    articles = []
    if not os.path.exists(KB_PATH):
        return articles
    for fname in os.listdir(KB_PATH):
        if fname.endswith(".json"):
            with open(os.path.join(KB_PATH, fname)) as f:
                articles.append(json.load(f))
    return articles


_KB_ARTICLES = _load_kb()


async def search_kb(
    inp: KBSearchInput,
    conversation_id: str = "unknown",
) -> KBSearchOutput:
    start = time.time()
    tool_name = "search_kb"
    STOPWORDS = {
        "a", "an", "the", "is", "are", "do", "does", "did", "i", "my", "me",
        "to", "for", "of", "on", "in", "how", "what", "can", "you", "your",
        "it", "this", "that", "with", "and", "or", "be", "was", "were",
    }
    try:
        query_lower = inp.query.lower()
        query_words = {w.strip("?.,!'\"") for w in query_lower.split()} - STOPWORDS

        scored = []
        for article in _KB_ARTICLES:
            keywords = [kw.lower() for kw in article.get("keywords", [])]
            title_words = {w.strip("?.,!'\"") for w in article.get("title", "").lower().split()} - STOPWORDS

            keyword_hits = sum(
                1 for kw in keywords
                if re.search(r"\b" + re.escape(kw) + r"\b", query_lower)
            )
            title_hits = len(query_words & title_words)
            score = keyword_hits * 3 + title_hits

            # Require at least one genuine keyword match — title-word overlap alone
            # (e.g. both query and title containing "streaming") isn't enough to qualify,
            # since that produces false positives between loosely related articles.
            if keyword_hits > 0:
                scored.append((score, article))

        scored.sort(key=lambda x: x[0], reverse=True)
        matches = [article for _, article in scored]

        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "success", latency)
        return KBSearchOutput(articles=matches[:3], found=len(matches) > 0)
    except Exception as e:
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "error", latency, str(e))
        return KBSearchOutput(articles=[], found=False)


async def create_handoff_ticket(
    inp: HandoffInput,
    conversation_id: str = "unknown",
) -> HandoffOutput:
    start = time.time()
    tool_name = "create_handoff_ticket"
    try:
        ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
        logger.info(
            "handoff_ticket_created",
            extra={
                "ticket_id": ticket_id,
                "customer_id": inp.customer_id,
                "reason": inp.reason,
                "conversation_id": conversation_id,
            },
        )
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "success", latency)
        return HandoffOutput(
            ticket_id=ticket_id,
            status="created",
            message=f"Your request has been escalated. A support agent will contact you soon. Reference: {ticket_id}",
            estimated_wait="2-4 hours",
        )
    except Exception as e:
        latency = round((time.time() - start) * 1000, 2)
        log_tool_call(conversation_id, tool_name, "error", latency, str(e))
        return HandoffOutput(
            ticket_id="ERROR",
            status="failed",
            message="Unable to create ticket. Please call support directly.",
            estimated_wait="unknown",
        )
