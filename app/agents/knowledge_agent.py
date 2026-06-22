"""
KnowledgeAgent: Answers general support questions using local KB.
Always includes source references or states when KB has no answer.
"""
from app.models.schemas import AgentResult, KBSearchInput
from app.tools.tools import search_kb
from app.db.llm_client import chat
from app.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a knowledge base support agent for StreamAssist.
Answer the customer's question using ONLY the provided KB articles.
Always cite the source article title at the end of your response.
Format: "Source: [article title]"

If the KB articles do not contain a relevant answer, say:
"I don't have a specific article for that. Please contact our support team for help."

Do NOT invent answers. Do NOT suggest things not in the KB articles."""


class KnowledgeAgent:
    async def run(
        self,
        message: str,
        customer_id: int | None,
        conversation_id: str,
    ) -> AgentResult:
        kb_result = await search_kb(
            KBSearchInput(query=message),
            conversation_id=conversation_id,
        )

        if not kb_result.found:
            return AgentResult(
                answer="I don't have a specific article for that in our knowledge base. Please contact our support team directly for assistance.",
                tools_used=["search_kb"],
                citations=[],
                next_action="escalate_if_needed",
                grounding_context="No relevant KB article found.",
            )

        articles_text = "\n\n".join(
            f"Article: {a.get('title', 'Unknown')}\nContent: {a.get('content', '')}"
            for a in kb_result.articles
        )

        answer = await chat(
            system=SYSTEM_PROMPT,
            user=f"Customer question: {message}\n\nKB Articles:\n{articles_text}",
            temperature=0.0,
        )

        return AgentResult(
            answer=answer,
            tools_used=["search_kb"],
            citations=[a.get("title", "") for a in kb_result.articles],
            next_action="none",
            grounding_context=articles_text,
        )
