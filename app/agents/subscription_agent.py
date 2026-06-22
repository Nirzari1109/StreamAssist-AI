"""
SubscriptionAgent: Handles subscription status and renewal questions.
Protects customer context — only returns data for the requesting customer.
"""
from app.models.schemas import AgentResult, SubscriptionInput
from app.tools.tools import get_customer_streaming_subscription
from app.db.database import AsyncSessionLocal
from app.db.llm_client import chat
from app.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a subscription support assistant for StreamAssist.
The customer has already been identified — their subscription data (or lack thereof) is provided below. Do NOT ask them for their customer ID or account details; that step is already done.

Answer the customer's question using ONLY the data below. Include:
- Plan name and current status (active/inactive/expired)
- Subscription start and end dates
- Whether auto-renew is enabled

If the data says "No subscription found", tell the customer clearly and suggest they sign up or contact support — do not ask for an ID, just report that no subscription exists for this account.
IMPORTANT: Never reveal or reference any other customer's subscription data. Never invent dates, plan names, or status not present in the data below."""


class SubscriptionAgent:
    async def run(
        self,
        message: str,
        customer_id: int | None,
        conversation_id: str,
    ) -> AgentResult:
        if customer_id is None:
            return AgentResult(
                answer="I need your customer ID to look up your subscription. Please provide your account details or log in to continue.",
                tools_used=[],
                next_action="request_auth",
            )

        async with AsyncSessionLocal() as db:
            sub_result = await get_customer_streaming_subscription(
                SubscriptionInput(customer_id=customer_id),
                db=db,
                conversation_id=conversation_id,
            )

        if not sub_result.found:
            context = f"No subscription found for customer {customer_id}."
        else:
            context = (
                f"Subscription found:\n"
                f"  Plan: {sub_result.plan_name}\n"
                f"  Status: {sub_result.status}\n"
                f"  Start date: {sub_result.start_date}\n"
                f"  End date: {sub_result.end_date}\n"
                f"  Auto-renew: {'Yes' if sub_result.auto_renew else 'No'}"
            )

        answer = await chat(
            system=SYSTEM_PROMPT,
            user=f"Customer question: {message}\n\n{context}",
            temperature=0.0,
        )

        return AgentResult(
            answer=answer,
            tools_used=["get_customer_streaming_subscription"],
            citations=[],
            next_action="none",
            grounding_context=context,
        )