"""
HumanHandoffAgent: Handles escalation and risky requests.
Creates support tickets. Never performs sensitive account mutations.
"""
from app.models.schemas import AgentResult, HandoffInput
from app.tools.tools import create_handoff_ticket
from app.observability.logger import get_logger

logger = get_logger(__name__)

# Patterns that should always be escalated, never executed directly
BLOCKED_MUTATIONS = [
    "cancel my subscription",
    "delete my account",
    "delete account",
    "remove my data",
    "change my password",
    "update my payment",
    "change payment",
    "refund",
]


class HumanHandoffAgent:
    async def run(
        self,
        message: str,
        customer_id: int | None,
        conversation_id: str,
    ) -> AgentResult:
        msg_lower = message.lower()
        is_blocked_mutation = any(pat in msg_lower for pat in BLOCKED_MUTATIONS)

        if is_blocked_mutation:
            reason = "sensitive_account_mutation_requested"
            summary = f"Customer requested a sensitive account operation: {message[:100]}"
        else:
            reason = "customer_requested_human"
            summary = f"Customer requested human support: {message[:100]}"

        ticket = await create_handoff_ticket(
            HandoffInput(
                summary=summary,
                reason=reason,
                customer_id=customer_id,
            ),
            conversation_id=conversation_id,
        )

        if is_blocked_mutation:
            answer = (
                f"For account changes like this, we need to verify your identity first. "
                f"I've created a support ticket ({ticket.ticket_id}) and a human agent will "
                f"assist you securely. Estimated wait: {ticket.estimated_wait}."
            )
        else:
            answer = (
                f"I've connected you with our support team. "
                f"Your ticket reference is {ticket.ticket_id}. "
                f"Estimated wait time: {ticket.estimated_wait}."
            )
        grounding_context = (
            f"Ticket ID: {ticket.ticket_id}\n"
            f"Ticket status: {ticket.status}\n"
            f"Estimated wait: {ticket.estimated_wait}\n"
            f"Reason: {reason}"
        )

        return AgentResult(
            answer=answer,
            tools_used=["create_handoff_ticket"],
            citations=[],
            next_action="await_human_agent",
            grounding_context=grounding_context,
        )