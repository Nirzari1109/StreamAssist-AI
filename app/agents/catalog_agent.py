"""
CatalogAgent: Answers questions about film catalog and streaming availability.
Uses search_film_catalog tool backed by Postgres.
"""
from app.models.schemas import AgentResult, FilmSearchInput
from app.tools.tools import search_film_catalog
from app.db.database import AsyncSessionLocal
from app.db.llm_client import chat
from app.observability.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a helpful catalog assistant for StreamAssist.
Answer the user's question using ONLY the search results provided below. These are the ONLY films that exist in the catalog — there are no other films, including ones you may know from general knowledge.

Rules:
1. If the search results list is empty, say no films matched and suggest refining the search. Do not mention any film by name.
2. If the search results contain films, you MUST list each one by its exact title, category, rating, rental rate, and streaming availability. Never skip a film that's in the results.
3. If the customer asked about a specific title (e.g. "Alien") and it does not exactly match any result, do NOT claim that title exists or is available anywhere. Instead say something like: "We don't have an exact match for '<their title>', but here's what we found:" and then list the actual results.
4. Never state or imply a film is available for streaming unless its streaming_available field says so in the results.
5. Never invent genre, rating, or plot details not present in the results.

Be concise and friendly."""

EXTRACT_KEYWORD_PROMPT = """Extract the core film title or search keyword from the customer's message.
Return ONLY the keyword/title, nothing else. No punctuation, no explanation.

Examples:
"Is Alien available for streaming?" -> Alien
"Do you have any action movies?" -> action
"What's the rental rate for Titanic?" -> Titanic
"Show me comedies" -> comedy"""


class CatalogAgent:
    async def run(
        self,
        message: str,
        customer_id: int | None,
        conversation_id: str,
    ) -> AgentResult:
        keyword = await chat(
            system=EXTRACT_KEYWORD_PROMPT,
            user=message,
            max_tokens=20,
            temperature=0.0,
        )
        keyword = keyword.strip().strip('"').strip("'") or message

        async with AsyncSessionLocal() as db:
            search_result = await search_film_catalog(
                FilmSearchInput(query=keyword),
                db=db,
                conversation_id=conversation_id,
            )

        context = ""
        if search_result.total == 0:
            context = "No films matched the search query."
        else:
            films_text = []
            for f in search_result.films:
                streaming = "✓ Available for streaming" if f.get("streaming_available") else "✗ Not available for streaming"
                films_text.append(
                    f"- {f['title']} | Category: {f.get('category', 'N/A')} | "
                    f"Rating: {f.get('rating', 'N/A')} | "
                    f"Rental rate: ${f.get('rental_rate', 'N/A')} | {streaming}"
                )
            context = "Search results:\n" + "\n".join(films_text)

        answer = await chat(
            system=SYSTEM_PROMPT,
            user=f"Customer question: {message}\n\n{context}",
            temperature=0.0,
        )

        return AgentResult(
            answer=answer,
            tools_used=["search_film_catalog"],
            citations=[f["title"] for f in search_result.films],
            next_action="none",
            grounding_context=context,
        )