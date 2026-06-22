"""
Pydantic schemas for request/response contracts.
All agent interactions are typed and validated.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    customer_id: Optional[int] = Field(None, description="Customer ID from Pagila")
    conversation_id: Optional[str] = Field(None, description="Unique conversation ID")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")


class AgentResponse(BaseModel):
    conversation_id: str
    intent: str
    selected_agent: str
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    tools_used: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    next_action: str = "none"
    guardrail_result: dict[str, Any] = Field(default_factory=dict)


class TriageResult(BaseModel):
    intent: str
    selected_agent: str
    confidence: float
    reason: str


class AgentResult(BaseModel):
    answer: str
    tools_used: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    next_action: str = "none"
    # Raw grounded data the agent used. Guardrail uses this to detect hallucinations.
    grounding_context: str = ""


class GuardrailResult(BaseModel):
    triggered: bool
    reason: Optional[str] = None
    safe_answer: Optional[str] = None
    checks_passed: list[str] = Field(default_factory=list)


# Tool input/output schemas
class FilmSearchInput(BaseModel):
    query: str = Field(..., description="Film title or keyword to search")


class FilmSearchOutput(BaseModel):
    films: list[dict[str, Any]]
    total: int


class SubscriptionInput(BaseModel):
    customer_id: int = Field(..., description="Customer ID")


class SubscriptionOutput(BaseModel):
    customer_id: int
    found: bool
    plan_name: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    auto_renew: Optional[bool] = None
    error: Optional[str] = None


class RentalHistoryInput(BaseModel):
    customer_id: int = Field(..., description="Customer ID")
    limit: int = Field(default=5, ge=1, le=20)


class RentalHistoryOutput(BaseModel):
    customer_id: int
    rentals: list[dict[str, Any]]
    total: int


class KBSearchInput(BaseModel):
    query: str = Field(..., description="Support question to search KB")


class KBSearchOutput(BaseModel):
    articles: list[dict[str, Any]]
    found: bool


class HandoffInput(BaseModel):
    summary: str = Field(..., description="Issue summary")
    reason: str = Field(..., description="Reason for escalation")
    customer_id: Optional[int] = None


class HandoffOutput(BaseModel):
    ticket_id: str
    status: str
    message: str
    estimated_wait: str
