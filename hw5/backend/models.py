"""Typed records shared by the agent team, the audit trail and (later) the API."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

StepType = Literal["model_call", "tool_call", "delegation"]


class PaymentRequest(BaseModel):
    """A payment an agent prepared. It stays pending until a human approves it."""

    id: int
    ticket_id: int
    kind: str
    ref_id: int
    payee: str
    amount: float
    reason: Optional[str] = None
    prepared_by: str
    status: str = "pending"


class AgentReport(BaseModel):
    """What one agent run produced."""

    agent: str
    called_by: Optional[str] = None
    task: str
    output: str
    depth: int = 0
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tools_used: list[str] = Field(default_factory=list)
    delegated_to: list[str] = Field(default_factory=list)


class AgentEvent(BaseModel):
    """One audit-trail entry: a model call, a tool call or a delegation."""

    timestamp: str
    run_id: str
    ticket_id: int
    agent: str
    step_type: StepType
    tool_or_target: Optional[str] = None
    args: Optional[str] = None
    result: Optional[str] = None
    tokens: Optional[dict[str, int]] = None
    stop_reason: Optional[str] = None


class TicketRunResult(BaseModel):
    """The outcome of running the team on one ticket."""

    run_id: str
    ticket_id: int
    outcome: str
    stopped_reason: Optional[str] = None
    agents_involved: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    payment_requests: list[PaymentRequest] = Field(default_factory=list)
    human_approval_needed: bool = False
    approval_amount: float = 0.0
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    reports: list[AgentReport] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
