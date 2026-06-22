"""
RentalHistoryAgent: Summarizes recent rental history for a customer.
"""
from app.models.schemas import AgentResult, RentalHistoryInput
from app.tools.tools import get_customer_rental_history
from app.db.database import AsyncSessionLocal
from app.db.llm_client import chat
from app.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a rental history assistant for StreamAssist.
Summarize the customer's recent rental history in a friendly, easy-to-read way.
List titles and dates. If no rentals exist, tell the customer kindly.
Do NOT include payment amounts or financial details in your summary."""


class RentalHistoryAgent:
    async def run(
        self,
        message: str,
        customer_id: int | None,
        conversation_id: str,
    ) -> AgentResult:
        if customer_id is None:
            return AgentResult(
                answer="I need your customer account to show rental history. Please log in and try again.",
                tools_used=[],
                next_action="request_auth",
            )

        async with AsyncSessionLocal() as db:
            history = await get_customer_rental_history(
                RentalHistoryInput(customer_id=customer_id, limit=5),
                db=db,
                conversation_id=conversation_id,
            )

        if history.total == 0:
            context = "No rental history found for this customer."
        else:
            lines = [
                f"  - {r['title']} (rented: {r.get('rental_date', 'N/A')}, returned: {r.get('return_date', 'not yet')})"
                for r in history.rentals
            ]
            context = f"Recent rentals ({history.total}):\n" + "\n".join(lines)

        answer = await chat(
            system=SYSTEM_PROMPT,
            user=f"Customer question: {message}\n\n{context}",
            temperature=0.0,
        )

        return AgentResult(
            answer=answer,
            tools_used=["get_customer_rental_history"],
            citations=list(dict.fromkeys(r["title"] for r in history.rentals)),
            next_action="none",
            grounding_context=context,
        )
