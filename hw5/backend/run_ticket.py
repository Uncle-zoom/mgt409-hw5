"""Run the agent team on one ticket from the terminal.

    .venv/bin/python backend/run_ticket.py 101

This calls the real model and writes to data/campus_customs_new.db (pending payments,
draft replies, ticket status) and to output/audit_trail.json.
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import AUDIT_PATH, ConfigError, LIMITS  # noqa: E402
from backend.team import create_team  # noqa: E402


async def main(ticket_id: int) -> int:
    try:
        team = create_team()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    async with team:
        result = await team.run_ticket(ticket_id)
    print(result.outcome)
    print("\n--- run summary ---")
    print(f"run_id:        {result.run_id}")
    print(f"agents:        {' -> '.join(result.agents_involved)}")
    print(f"tools used:    {', '.join(result.tools_used)}")
    for p in result.payment_requests:
        print(f"payment:       #{p.id} {p.kind} {p.payee} {p.amount:.2f} ({p.status})")
    print(f"human approval needed: {'yes' if result.human_approval_needed else 'no'}"
          + (f" (${result.approval_amount:,.2f})" if result.human_approval_needed else ""))
    print(f"model requests: {result.requests}, tokens: {result.total_tokens} "
          f"(limit {LIMITS.total_tokens_per_ticket})")
    if result.stopped_reason:
        print(f"STOPPED: {result.stopped_reason}")
    print(f"audit trail:   {AUDIT_PATH}")
    return 1 if result.stopped_reason else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ticket_id", type=int, help="ticket id, e.g. 101, 102 or 103")
    sys.exit(asyncio.run(main(parser.parse_args().ticket_id)))
