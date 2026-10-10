"""The Campus Customs agent team (PydanticAI).

Five agents, one prompt file each. Every agent reaches shop data only through the
campus-customs MCP server (stdio) and can hand work to the others with delegate().
"""
import json
import sys
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, UsageLimitExceeded, UsageLimits
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets import FilteredToolset
from pydantic_ai.usage import RunUsage

from fastmcp.client.transports import StdioTransport

from . import audit as audit_mod
from .audit import AuditTrail
from .config import (
    AGENT_NAMES,
    AUDIT_PATH,
    LIMITS,
    MCP_SERVER_PATH,
    PORTKEY_BASE_URL,
    PROMPTS_DIR,
    Settings,
    load_settings,
)
from .models import AgentEvent, AgentReport, PaymentRequest, TicketRunResult

# Which MCP tools each agent may see (from the "Tools:" lines in the prompt files).
# delegate is added to every agent separately.
TOOL_ACCESS: dict[str, set[str]] = {
    "boss": {"get_ticket", "get_desk_date", "list_pending_payments", "update_ticket_status"},
    "inventory": {"check_stock", "list_vendors"},
    "accounting": {"get_invoice", "get_cash_balance", "get_pricing", "get_desk_date", "prepare_payment"},
    "facilities": {"get_lease", "get_desk_date"},
    "customer_service": {"get_ticket", "record_customer_reply"},
}


# Tools that move money or run the dashboard. No agent gets them: they are left out of every
# list above, and the server only registers them when started with --admin (the agent team
# never does). The import-time check below keeps it that way.
ADMIN_ONLY_TOOLS = {"list_tickets", "list_all_pending_payments", "approve_payment", "reject_payment"}
assert not ADMIN_ONLY_TOOLS & set().union(*TOOL_ACCESS.values()), "an agent was given an admin tool"


@dataclass
class RunState:
    """Everything shared by all agents while one ticket is worked."""

    usage: RunUsage = field(default_factory=RunUsage)
    handoffs: set[tuple[str, str]] = field(default_factory=set)
    agents_involved: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    payments: dict[int, PaymentRequest] = field(default_factory=dict)
    reports: list[AgentReport] = field(default_factory=list)
    redactions: set[str] = field(default_factory=set)


@dataclass
class TicketDeps:
    ticket_id: int
    run_id: str
    agent: str
    depth: int
    team: "AgentTeam"
    state: RunState


def load_prompts(prompts_dir: Path = PROMPTS_DIR) -> dict[str, str]:
    return {name: (prompts_dir / f"{name}.md").read_text(encoding="utf-8") for name in AGENT_NAMES}


def build_model(settings: Settings) -> Model:
    client = AsyncOpenAI(
        api_key=settings.api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": settings.api_key, "x-portkey-provider": "openai"},
        timeout=LIMITS.model_call_timeout_seconds,
        max_retries=0,  # so the timeout really is the cap for one model call
    )
    return OpenAIResponsesModel(settings.model, provider=OpenAIProvider(openai_client=client))


async def delegate(ctx: RunContext[TicketDeps], to_agent: str, task: str) -> str:
    """Hand a task to another agent on the team and get their report back.

    to_agent is one of: boss, inventory, accounting, facilities, customer_service
    (never yourself). task is a clear paragraph with the ticket id and the facts the
    other agent needs. Only delegate what you need. The same handoff can't be repeated.
    """
    deps = ctx.deps
    team, state = deps.team, deps.state

    def blocked(reason: str) -> str:
        team.log(deps, "delegation", to_agent, {"task": task}, f"BLOCKED: {reason}")
        return f"Handoff blocked: {reason}"

    if to_agent not in team.agents:
        return blocked(f"unknown agent '{to_agent}'. Choose from {list(team.agents)}.")
    if to_agent == deps.agent:
        return blocked("you can't delegate to yourself.")
    if deps.depth + 1 > LIMITS.max_delegation_depth:
        return blocked(f"max delegation depth {LIMITS.max_delegation_depth} reached. Finish with what you have.")
    if (deps.agent, to_agent) in state.handoffs:
        return blocked(f"{deps.agent} already handed work to {to_agent} on this ticket.")

    state.handoffs.add((deps.agent, to_agent))
    child = replace(deps, agent=to_agent, depth=deps.depth + 1)
    outcome = "stopped before finishing"
    try:
        report = await team.run_agent(child, task, called_by=deps.agent)
        outcome = report.output
        return f"Report from {to_agent}:\n{report.output}"
    finally:
        team.log(deps, "delegation", to_agent, {"task": task}, outcome)


class AgentTeam:
    def __init__(
        self,
        settings: Settings,
        *,
        model: Model | None = None,
        server_path: Path = MCP_SERVER_PATH,
        audit_path: Path = AUDIT_PATH,
        prompts_dir: Path = PROMPTS_DIR,
    ):
        self.settings = settings
        self.audit = AuditTrail(audit_path, secrets=[settings.api_key])
        model = model or build_model(settings)
        model_settings = {"timeout": LIMITS.model_call_timeout_seconds, "parallel_tool_calls": False}
        # One stdio connection to the MCP server, shared. Each agent sees only its own tools.
        self.mcp = MCPToolset(StdioTransport(command=sys.executable, args=[str(server_path)]))
        self.agents: dict[str, Agent[TicketDeps, str]] = {}
        for name, prompt in load_prompts(prompts_dir).items():
            allowed = TOOL_ACCESS[name]
            self.agents[name] = Agent(
                model,
                name=name,
                instructions=prompt,
                deps_type=TicketDeps,
                tools=[delegate],
                toolsets=[FilteredToolset(self.mcp, lambda ctx, td, allowed=allowed: td.name in allowed)],
                model_settings=model_settings,
            )
        self._stack: AsyncExitStack | None = None

    async def __aenter__(self) -> "AgentTeam":
        self._stack = AsyncExitStack()
        await self._stack.enter_async_context(self.mcp)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._stack:
            await self._stack.aclose()

    # -- audit -------------------------------------------------------------------------
    def log(
        self,
        deps: TicketDeps,
        step_type: str,
        tool_or_target: str | None = None,
        args: Any = None,
        result: Any = None,
        tokens: dict[str, int] | None = None,
        stop_reason: str | None = None,
    ) -> None:
        red = deps.state.redactions
        self.audit.append(
            AgentEvent(
                timestamp=audit_mod.now(),
                run_id=deps.run_id,
                ticket_id=deps.ticket_id,
                agent=deps.agent,
                step_type=step_type,
                tool_or_target=tool_or_target,
                args=None if args is None else self.audit.scrub(args, red),
                result=None if result is None else self.audit.scrub(result, red),
                tokens=tokens,
                stop_reason=stop_reason,
            )
        )

    def _note_tool_result(self, deps: TicketDeps, tool: str, content: Any) -> None:
        """Remember requester names (to scrub them) and payment requests (for the result)."""
        data = content
        if isinstance(content, str):
            try:
                data = json.loads(content)
            except ValueError:
                return
        if not isinstance(data, dict):
            return
        if tool == "get_ticket" and isinstance(data.get("ticket"), dict):
            deps.state.redactions |= audit_mod.name_variants(data["ticket"].get("requester", ""))
        if tool == "prepare_payment" and isinstance(data.get("payment_request"), dict):
            pr = PaymentRequest(**data["payment_request"])
            deps.state.payments[pr.id] = pr

    def _tool_args_for_log(self, tool: str, args: dict[str, Any]) -> Any:
        if tool == "record_customer_reply":  # a customer message can hold personal details
            return {"ticket_id": args.get("ticket_id"), "message_chars": len(str(args.get("message", "")))}
        return args

    # -- running -----------------------------------------------------------------------
    async def run_agent(self, deps: TicketDeps, task: str, called_by: str | None = None) -> AgentReport:
        state = deps.state
        if deps.agent not in state.agents_involved:
            state.agents_involved.append(deps.agent)
        agent = self.agents[deps.agent]
        prompt = f"Ticket id: {deps.ticket_id}\nTask{f' from {called_by}' if called_by else ''}: {task}"
        # Usage is shared across the whole ticket, so the token limit is ticket-wide. The request
        # limit is per agent run, so it is counted here from this run's own model responses.
        limits = UsageLimits(request_limit=None, total_tokens_limit=LIMITS.total_tokens_per_ticket)
        own_requests = own_in = own_out = 0
        tools_used: list[str] = []
        delegated_to: list[str] = []
        pending_calls: dict[str, ToolCallPart] = {}

        async with agent.iter(prompt, deps=deps, usage=state.usage, usage_limits=limits) as run:
            async for node in run:
                if not Agent.is_call_tools_node(node):
                    continue
                response: ModelResponse = node.model_response
                own_requests += 1
                own_in += response.usage.input_tokens
                own_out += response.usage.output_tokens
                calls = [p.tool_name for p in response.parts if isinstance(p, ToolCallPart)]
                text = " ".join(p.content for p in response.parts if isinstance(p, TextPart))
                self.log(
                    deps,
                    "model_call",
                    None,
                    None,
                    text or f"requested tools: {calls}",
                    tokens={
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens,
                        "total": response.usage.input_tokens + response.usage.output_tokens,
                    },
                    stop_reason=response.finish_reason,
                )
                if calls and own_requests >= LIMITS.request_limit_per_agent_run:
                    raise UsageLimitExceeded(
                        f"{deps.agent} reached its limit of {LIMITS.request_limit_per_agent_run} "
                        "model requests in one run"
                    )
                async with node.stream(run.ctx) as events:
                    async for event in events:
                        if isinstance(event, FunctionToolCallEvent):
                            pending_calls[event.part.tool_call_id] = event.part
                        elif isinstance(event, FunctionToolResultEvent):
                            call = pending_calls.pop(event.tool_call_id, None)
                            tool = call.tool_name if call else event.part.tool_name
                            args = call.args_as_dict() if call else {}
                            content = event.part.content
                            if tool == "delegate":
                                delegated_to.append(str(args.get("to_agent")))
                                continue  # logged as a "delegation" entry by delegate()
                            tools_used.append(tool)
                            state.tools_used.append(tool)
                            self._note_tool_result(deps, tool, content)
                            self.log(deps, "tool_call", tool, self._tool_args_for_log(tool, args), content)

        report = AgentReport(
            agent=deps.agent,
            called_by=called_by,
            task=task,
            output=run.result.output,
            depth=deps.depth,
            requests=own_requests,
            input_tokens=own_in,
            output_tokens=own_out,
            tools_used=tools_used,
            delegated_to=delegated_to,
        )
        state.reports.append(report)
        return report

    async def run_ticket(self, ticket_id: int, run_id: str | None = None) -> TicketRunResult:
        run_id = run_id or uuid.uuid4().hex[:12]
        state = RunState()
        deps = TicketDeps(ticket_id=ticket_id, run_id=run_id, agent="boss", depth=0, team=self, state=state)
        outcome, stopped = "", None
        try:
            report = await self.run_agent(deps, f"Work ticket {ticket_id}.")
            outcome = report.output
        except UsageLimitExceeded as exc:
            stopped = f"usage limit: {exc}"
            outcome = "Stopped: a usage limit was reached before the ticket was finished."
            self.log(deps, "model_call", None, None, stopped, stop_reason="limit_exceeded")
        except audit_mod.AuditError:
            raise  # never carry on without an audit trail
        except Exception as exc:  # model timeout, HTTP error, a model stuck on a bad tool call...
            stopped = f"{type(exc).__name__}: {exc}"
            outcome = "Stopped: the run failed before the ticket was finished."
            self.log(deps, "model_call", None, None, stopped, stop_reason="error")
        payments = list(state.payments.values())
        usage = state.usage
        return TicketRunResult(
            run_id=run_id,
            ticket_id=ticket_id,
            outcome=outcome,
            stopped_reason=stopped,
            agents_involved=state.agents_involved,
            tools_used=list(dict.fromkeys(state.tools_used)),
            payment_requests=payments,
            human_approval_needed=any(p.status == "pending" for p in payments),
            approval_amount=round(sum(p.amount for p in payments if p.status == "pending"), 2),
            requests=usage.requests,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
            reports=state.reports,
        )


def create_team(**kwargs: Any) -> AgentTeam:
    """Build the team from .env. Raises ConfigError unless MODEL is gpt-6-luna and a key is set."""
    return AgentTeam(load_settings(), **kwargs)
