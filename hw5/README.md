# MGT 409 Homework 5: Campus Customs ops desk

An operations desk for Campus Customs, the Yale merch shop on Chapel Street. Five PydanticAI agents (Boss, Inventory, Accounting, Facilities, Customer Service) on `gpt-6-luna` work through support tickets. They get shop data only through a FastMCP server over SQLite, and a FastAPI backend and a React board sit on top. Agents can only prepare payments. Humans approve every payment on the board.

## How it fits together

| Part | Where | What it does |
|---|---|---|
| Agents | `backend/team.py`, `backend/prompts/` | Five agents, one prompt file each, with limits and an audit trail. |
| MCP server | `mcp_server/server.py` | FastMCP over stdio, reading and writing `data/campus_customs_new.db`. |
| API | `backend/main.py` | FastAPI routes for tickets, runs, events, approvals, cash and reset. |
| Board | `frontend/` | React + Vite + TypeScript departures-board dashboard. |
| Data | `data/` | `campus_customs.db` (the original) and `campus_customs_new.db` (the working copy). |
| Write-ups | `output/` | Harness, plan vs. actual, cash, reflection, screenshots and audit trail. |

## Run it

You need Python 3 and Node.js.

1. **Add your key.** Copy `.env.example` to `.env` and put your key in `PORTKEY_API_KEY`. Leave `MODEL=gpt-6-luna` as it is: the backend refuses to start with any other model.

   ```bash
   cp .env.example .env
   ```

2. **Make the virtual environment and install.**

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. **Start from a clean database.** The committed working copy is in its final state (see below), so copy the original over it, or press **Reset desk** on the board later:

   ```bash
   cp data/campus_customs.db data/campus_customs_new.db
   ```

   Do this before a full three-ticket run.

4. **MCP server.** You don't need to start it. The backend starts it automatically, and Claude Code starts it through `.mcp.json` when you open this folder. To run it by hand:

   ```bash
   .venv/bin/python mcp_server/server.py
   ```

5. **Backend** (port 8000):

   ```bash
   cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000
   ```

6. **Board** (in a second terminal):

   ```bash
   cd frontend && npm install && npm run dev
   ```

   Then open http://localhost:5173. The backend only allows requests from that address, so keep the board on port 5173.

On the board, pick a ticket and press Run. When Accounting prepares a payment it shows up under "Waiting for your OK", and nothing is paid until you approve it.

You can also run one ticket from the terminal, without the board:

```bash
.venv/bin/python backend/run_ticket.py 101
```

## What's committed

- `data/campus_customs_new.db` is committed **in its final state after my run**: checking cash is $160.00 and all three tickets are resolved. `data/campus_customs.db` is the untouched original. To run the tickets again, reset first (step 3).
- `output/` has the write-ups:
  - `harness.md`: the database, MCP tools, the five agents, API routes, the dashboard and the safety rules, plus the final run.
  - `desk_tickets.html`: the plan next to what actually happened for each ticket, the cash ledger and my reflection.
  - `resolved_tickets.json`: final status, outcome, agent contributions, approvals and draft replies.
  - `resolved_board.html` and `resolved_board_images/`: screenshots of the board after each run.
  - `design.md`: how the dashboard is laid out and why.
  - `audit_trail.json`: every model call, tool call and delegation, appended per run.
  - `mcp_smoke.json` and `github_url.txt`.
- `AI_prompts.md` is the log of my prompts for this homework.
- `.env` is not committed. `.env.example` shows what it needs.
