# AI Prompts Log: Homework 5 (Campus Customs Ops Desk)

Running log of what I typed to Claude Code for this homework.

## Setup

```text
use Homework 5 folder for this project, It's an operations desk for Campus Customs (the Yale merch shop) where a team of AI agents works through support tickets. Create:
- mcp_server/ (empty for now)
- backend/ with a FastAPI main.py that only has a GET /health route, plus an empty prompts/ folder
- frontend/ as a Vite + React + TypeScript app from the official react-ts template
- output/ for my write-ups
- requirements.txt at the hw5 root: fastapi, uvicorn, pydantic-ai, openai, python-dotenv, mcp
- .env.example with placeholders only: PORTKEY_API_KEY=your-key-here and MODEL=gpt-6-luna
- .gitignore that ignores .env, .venv/, node_modules/, __pycache__/, frontend/dist/ and .DS_Store. Do
NOT ignore data/ or .db files. Both database files get committed for this homework. Don't add any
blanket *.png or *.jpg rules, because I'll commit screenshots in output/.
- a .venv in Homework 5 with the requirements installed.
My database is already in data/. Don't touch it and don't build any features yet.
```

---

## Problem 1: Vibe coder prompts

### Prompt I typed

```text
Create AI_prompts.md in the root of this project. It's my running log of what I type to you for Homework 5. 

Add a "Setup" section first with the setup prompt I sent you earlier, pasted word for word. Then add one section per problem, 1 through 11, each with: the problem number and title, "Prompt I typed" (my prompt exactly as I sent it), and "Follow-up" (any follow-up I send, plus one sentence on what was missing after the first try).

From now on, after each problem, add my prompts to the right section without changing my wording.

Problem titles:
1 Vibe coder prompts
2 Study the Campus Customs database
3 Build the MCP server
4 Add the MCP server to vibe coder and test each tool
5 Build the agent team and grow the MCP tools
6 Plan the three tickets
7 Backend routes
8 Agent dashboard
9 Resolve the tickets
10 Reflection
11 Submit to GitHub
```

### Follow-up

_(none yet)_

---

## Problem 2: Study the Campus Customs database

### Prompt I typed

```text
Open data/campus_customs.db read-only and don't change anything in it. List every table with every column, its type and the row count.

Then copy the file byte-for-byte to data/campus_customs_new.db. That's the working copy later problems will update. The original must stay untouched for the rest of the homework.

Next, read the tickets table. For each of the three open tickets, follow every id or reference it mentions into the other tables (inventory, pricing, vendors, leases, cash_accounts, payments, invoices, desk) and show me the chain of actual rows, so I can see what each ticket needs to get resolved. Also show me the desk table, especially date_today.

Then start output/harness.md with a title and a "## Database" section: for every table, list its fields and one short line on why that table matters to the agents (which ticket or which agent needs it). Only describe what's really in the database. If something looks odd or missing, say so instead of guessing.

Finally, log this prompt word for word under Problem 2 in AI_prompts.md.
```

### Follow-up

```text
One fix in harness.md: you wrote there are no declared foreign keys, but tickets declares FOREIGN KEY lease_id → leases(id) and invoice_id → invoices(id). Correct that line, and log this as my Problem 2 follow-up with one sentence on what was wrong.
```

What was missing after the first try: I read the schema with column info only and never checked the foreign key list, so I wrongly said the database had no declared foreign keys.

---

## Problem 3: Build the MCP server

### Prompt I typed

```text
Write an MCP server in mcp_server/server.py using FastMCP from the mcp package, named "campus-customs", running over stdio. It reads data/campus_customs_new.db. Build the database path from where server.py lives, not the current folder. Open the database read-only for these tools.

Add three read-only tools, one per open ticket:
- check_stock(sku, size): reads inventory. Returns the qty and location for that size, plus every other size of the same sku with its qty. This is for ticket 101 (tee size S is at 0, so agents need to see the other sizes).
- get_lease(lease_id): reads leases and desk. Returns the lease row plus desk.date_today and how many days until next_due, counted from desk.date_today, never the real clock. This is for ticket 102 (rent due 2026-09-02).
- get_pricing(sku): reads pricing. Returns unit_cost, list_price and the margin per unit. This is for ticket 103 (any bulk discount has to stay above cost).

Each tool uses parameterized SQL, returns only real database values, and returns a clear "not found" result if nothing matches. Never make data up. Give each tool a docstring that says when an agent should use it.

In output/harness.md add a "## MCP Tools" section. For each tool: the table it reads, which ticket it unlocks, and one specific sentence on why it's the right tool for that ticket, using the real numbers. Also write a short mcp_server/README.md covering what the server is for, which database file it uses, and the three tools. Don't connect or run it yet.

Log this prompt word for word under Problem 3 in AI_prompts.md.
```

### Follow-up

_(none yet)_

---

## Problem 4: Add the MCP server to vibe coder and test each tool

### Prompt I typed

```text
Create .mcp.json at the root of this project so Claude Code can use my MCP server. Add one server called "campus-customs" that runs mcp_server/server.py with .venv/bin/python. Use relative paths only and don't put any keys or secrets in the file.

Also change the mcp line in requirements.txt to mcp>=1.30,<2, since server.py uses FastMCP from mcp 1.x.

Log this prompt under Problem 4 in AI_prompts.md.
```

Three test questions I asked after restarting, so the MCP server was loaded:

```text
Do we have the Classic Bulldog Tee in size S right now?
```

```text
When is rent due on the Chapel Street shop and how many days do we have?
```

```text
What's our cost and list price on the navy hoodie?
```

Prompt asking for the smoke test file and this log:

```text
Save output/mcp_smoke.json with one entry for each of the three questions I just asked: my exact question, the name of the MCP tool you called, and the tool's raw output copied exactly, not summarized. Then log my three questions and this prompt under Problem 4 in AI_prompts.md. Also log my "check if the campus-customs MCP server is loaded" message as a Problem 4 follow-up, with one sentence saying the first session didn't load the server until I restarted.
```

### Follow-up

```text
Check if the campus-customs MCP server from .mcp.json in this folder is loaded. If it isn't, run "claude mcp list" and tell me what it says, but don't change any files.
```

What was missing after the first try: the session where I created `.mcp.json` didn't load the campus-customs server, so the tools only appeared after I restarted.

---

## Problem 5: Build the agent team and grow the MCP tools

### Prompt I typed

Prompt 1, creating the prompt files:

```text
Create five prompt files in backend/prompts/ with exactly the text I give below. 
Don't edit my wording. Log this prompt under Problem 5 in AI_prompts.md (you can note "five agent prompt files, full text in backend/prompts/" instead of pasting all five again).

(five agent prompt files, full text in backend/prompts/: boss.md, inventory.md, accounting.md, facilities.md, customer_service.md)

then :
```

Prompt 2, building the agent team:

```text
Now build the agent team with PydanticAI in backend/ using the five prompt files you just created. Load each one at startup and don't change them.

Model: every agent uses Portkey (PORTKEY_API_KEY from .env, base URL https://api.portkey.ai/v1) with gpt-6-luna. Read MODEL from .env and refuse to start if it isn't gpt-6-luna. Check the installed pydantic-ai version's API before writing code.

Shop data: every agent gets shop facts only through my campus-customs MCP server (mcp_server/server.py over stdio) as a toolset. No sqlite or SQL anywhere in backend/.

Delegation: every agent gets a delegate(to_agent, task) tool that can call any other agent except itself, with shared usage across the whole ticket. Max delegation depth 3, and block the same handoff twice in one run.

Add these MCP tools to mcp_server/server.py:
- get_ticket(ticket_id) reads tickets
- get_desk_date() reads desk
- get_invoice(invoice_id) reads invoices + vendors, with days overdue counted from desk.date_today
- get_cash_balance() reads cash_accounts
- list_vendors() reads vendors
- prepare_payment(ticket_id, kind, ref_id, payee, amount, reason, prepared_by) writes a row to a pending_payments table (create it if it doesn't exist) with status pending. It must never touch cash_accounts or payments.
- update_ticket_status(ticket_id, status, note) allows open, awaiting_approval or resolved, and refuses resolved while that ticket has a pending payment.
- record_customer_reply(ticket_id, message) saves a draft to a customer_replies table (create if missing). Nothing is sent.

No MCP tool may change cash_accounts. Keep the original three tools as they are.

Types in backend/models.py: AgentReport, AgentEvent, PaymentRequest, TicketRunResult.

Limits, in one config block and enforced in code: request limit 8 per agent run, 60,000 total tokens per ticket, 60 seconds per model call, max delegation depth 3.

Audit: append one JSON entry to output/audit_trail.json for every model call, tool call and delegation: timestamp, run_id, ticket_id, agent, step type, tool or target, short args, short result, tokens, stop reason. Never wipe the file. No keys or personal data.

Add a small script backend/run_ticket.py so I can test one ticket from the terminal.

Update output/harness.md: "## Agents" (role, prompt file, tools, usual handoffs), the full "## MCP Tools" list with the table each tool uses, and "## Safety and Limits" (real-business guardrails plus the exact numbers). Update mcp_server/README.md to match.

Log this prompt under Problem 5 in AI_prompts.md.
```

### Follow-up

```text
Test run on ticket 101 showed a gap: accounting saw invoice 501 was open and 3 days overdue but never prepared the payment, so the ticket stayed open. Fix the prompt files:
- In accounting.md, add: when an open vendor invoice is blocking an order and it's due or overdue by desk.date_today, prepare the payment with prepare_payment (if checking can cover it) so a human can approve it, then tell whoever asked that it's waiting for approval.
- In boss.md, add: if any agent prepared a payment on this ticket, set the status to awaiting_approval, never leave it open.
Then run ticket 101 once with backend/run_ticket.py and show me the summary. After the test, copy data/campus_customs.db over data/campus_customs_new.db so the working copy is clean again. Log this as my Problem 5 follow-up with one sentence on what was missing.
```

What was missing after the first try: the accounting and boss prompts never told the agents to prepare the overdue invoice payment or to set the ticket to awaiting_approval, so ticket 101 stayed open.

Second follow-up:

```text
The second test run worked but showed three problems:
1. Agents called back the agent who called them (customer_service called inventory and accounting again for facts it already had), which pushed one ticket to 29 requests and 41k tokens. Add this rule to all five prompt files: "If another agent handed you a task, it already gave you the facts. Don't delegate back to the agent who called you. Only ask a different agent if a fact is truly missing."
2. Add an MCP tool list_pending_payments(ticket_id) that reads pending_payments, and give it to boss. In boss.md, add: "Before setting the status, call list_pending_payments and include each payment's payee and amount in your summary."
3. Raise the per-ticket token limit from 60,000 to 100,000 in config.py and update the number in harness.md.
Run ticket 101 once more with run_ticket.py and show me the summary (agents, payments, requests, tokens). Then copy data/campus_customs.db over data/campus_customs_new.db again. Log this as my second Problem 5 follow-up with one sentence on what was missing.
```

What was missing after the first follow-up: the prompts let agents call back the agent who called them, which wasted requests and tokens, and the boss had no tool to list pending payments, so its summary didn't name the payee and amount.

Third follow-up:

```text
Yes, add the customer reply line. In boss.md add: "For customer_order and price_override tickets, once the specialists are done, hand the confirmed facts (stock, lead time, approved price, what's waiting on approval) to customer_service to save a draft reply. Rent notices don't need a customer reply." Don't run a test this time. Log this as my third Problem 5 follow-up with one sentence on what was missing.
```

What was missing after the second follow-up: nothing in the boss prompt told it to hand the confirmed facts to customer_service, so the last run saved no draft reply for the customer.

---

## Problem 6: Plan the three tickets

### Prompt I typed

```text
Build output/desk_tickets.html as one self-contained page (inline CSS and JS, no server, opens by double-click) with five tabs: Ticket 101, Ticket 102, Ticket 103, Cash, Reflection. Cash and Reflection just say "Coming later (Problem 9 / Problem 10)" for now.

Each ticket tab shows a short ticket summary, then two sections: "Expected" with my plan below, and "Actual", left empty with the note "Filled after the run (Problem 9)". For Expected, show a small table: Boss's first call and why, the delegation chain in order, MCP tools expected, and the human approval expected. Put my plan in exactly as I wrote it. Make it clean and easy to read.

My plan:

Ticket 101: Tauhid Zaman wants a Bulldog tee in size S.
- Boss first calls Inventory, because this is a customer order and the first question is whether we can fill it.
- Chain: Boss → Inventory (check_stock shows size S is at 0. list_vendors shows Bulldog Print Co reprints in 5 days) → Accounting (get_invoice shows the reprint invoice 501, $840, was due 08-28 and is 3 days overdue by the desk date. get_cash_balance shows $3,400, so it prepares the $840 payment) → back to Boss (list_pending_payments, then status awaiting_approval) → Customer Service (draft reply: S is out, the reprint is waiting on payment, other sizes are available now).
- Tools: get_ticket, get_desk_date, check_stock, list_vendors, get_invoice, get_cash_balance, prepare_payment, list_pending_payments, update_ticket_status, record_customer_reply.
- Human approval: yes, $840 to Bulldog Print Co. Nothing ships until it's paid.

Ticket 102: Elm City Properties says rent is due.
- Boss first calls Facilities, because the lease is facilities' job and the notice should be checked before any money moves.
- Chain: Boss → Facilities (get_lease confirms the same landlord, $2,400, due 09-02, which is 2 days from the desk date) → Accounting (get_cash_balance, then prepare_payment for $2,400) → back to Boss (list_pending_payments, awaiting_approval). Inventory and Customer Service aren't needed.
- Tools: get_ticket, get_desk_date, get_lease, get_cash_balance, prepare_payment, list_pending_payments, update_ticket_status.
- Human approval: yes, $2,400 to Elm City Properties.

Ticket 103: Yale AI Club wants 20 navy hoodies in size M at a bulk discount.
- Boss first calls Accounting, because the request is about price and a discount is a money decision first.
- Chain: Boss → Accounting (get_pricing shows cost $22 and list $58, so at most 15% off is $49.30 each, $986 for 20, still well above cost) → Inventory (check_stock shows only 8 in size M, with L 14, XL 6, S 4) → back to Boss → Customer Service (draft offer: 8 in M now at $49.30, the rest in another size or after a restock). No payment is expected, so the status should be resolved.
- Tools: get_ticket, get_desk_date, get_pricing, check_stock, list_pending_payments, update_ticket_status, record_customer_reply.
- Human approval: no, unless the agents try a restock. Restocking 12 hoodies costs $264, but if 101 and 102 are paid first, only $160 is left, so I expect Accounting to flag that it can't cover it.

Expected cash: $3,400 − $840 − $2,400 = $160 at the end.

Log this prompt under Problem 6 in AI_prompts.md.
```

### Follow-up

_(none yet)_

---

## Problem 7: Backend routes

### Prompt I typed

```text
Add the API routes for the dashboard in backend/main.py with FastAPI. Keep all database access going through my campus-customs MCP server. No sqlite in backend/.

New MCP tools in mcp_server/server.py, which NO agent gets (leave them out of every agent's tool list in team.py):
- list_tickets(): every ticket with id, type, requester, subject and status.
- approve_payment(payment_id, approved_by): only if the payment is still pending, and in one transaction: subtract the amount from checking in cash_accounts, insert a row in payments (kind, ref_id, amount, account 'checking', paid_at = desk.date_today, approved_by), mark the pending payment approved, mark invoice 501 'paid' if it was an invoice, and set the ticket to resolved if it has no other pending payments. Approving twice must fail.
- reject_payment(payment_id): marks it rejected and never touches cash.
- list_all_pending_payments(): every payment still waiting for approval.
Give these their own guarded connection that only allows those writes. The agent tools keep their current guard.

Routes:
- GET /api/tickets: the three tickets and their status.
- POST /api/tickets/{ticket_id}/run: starts the agent team on that ticket in the background and returns a run_id right away. Only one run at a time; return 409 if one is already running.
- GET /api/events?run_id=...&after=N: that run's events in order (agent, step type, tool or delegation target, short text), read from what the audit trail recorded for that run_id, plus whether the run is finished and its final summary.
- GET /api/approvals: payments waiting for a human.
- POST /api/approvals/{payment_id}/approve and POST /api/approvals/{payment_id}/reject: the only way money moves, and only from a human click.
- GET /api/cash: the checking balance.
- POST /api/reset: refuses while a run is going. Copies data/campus_customs.db over data/campus_customs_new.db and clears in-memory run state. Never touches output/audit_trail.json.

Allow CORS from http://localhost:5173. "uvicorn main:app --reload --port 8000" from inside backend/ must work.

Update output/harness.md: an "## API Routes" section with one line per route, and in Safety and Limits explain that approve_payment is hidden from every agent and only the human approve route can call it. Update mcp_server/README.md.

Log this prompt under Problem 7 in AI_prompts.md.
```

### Follow-up

_(none yet)_

---

## Problem 8: Agent dashboard

### Prompt I typed

```text
Build the ops desk dashboard in frontend/ (React + Vite + TypeScript) that talks to my backend at http://localhost:8000.

Look and feel: Make it feel like an airport departures board: each ticket is a flight that flips from OPEN to RESOLVED, each agent is a gate with its own color, and cash is shown like a scoreboard. Make it look like a real Campus Customs tool people would want to sit at, not the default Vite page. Remove every Vite leftover (logos, hero.png, the default App.css and index.css rules, the "Vite + React" title and favicon).

It must:
1. List all three tickets with their status (open / awaiting approval / resolved) from GET /api/tickets.
2. Let me pick a ticket and press Run (POST /api/tickets/{id}/run). Disable Run while a run is going.
3. While it runs, poll GET /api/events every second and show each agent in its own lane, with its own color, icon and role label: Boss, Inventory, Accounting, Facilities, Customer Service. Show each message and tool call as it happens, and show a delegation as an arrow or "Boss → Inventory" chip.
4. When the run finishes, mark the ticket with its new status and show a summary card for each agent that took part: what it found, what it did, the tools it used.
5. Show payments waiting for approval (GET /api/approvals) as cards with payee, amount, reason and which agent prepared them, with Approve and Reject buttons. Ask "Are you sure?" inside the page (no browser popups) before approving.
6. Show the checking balance (GET /api/cash) big and clear, and animate it dropping after an approval. Also show the "after pending" amount.
7. A Reset button (POST /api/reset) with an in-page confirm, for starting a clean run.

Then write output/design.md: the layout, how each agent looks different, how resolved tickets and cash show up, the creative choices and why each one helps the people working the desk. Only describe what's actually built.

Log this prompt under Problem 8 in AI_prompts.md.
```

### Follow-up

_(none yet)_

---

## Problem 9: Resolve the tickets

### Prompt I typed

```text
I just finished a clean full run of all three tickets on the board. Use only these three final runs from output/audit_trail.json: ticket 101 = run 01a63e5fc065, ticket 102 = run 4cc7c3ef82c3, ticket 103 = run 1690588b0383. Ignore the earlier test runs. Don't run any agents and don't change either database.

1. In output/desk_tickets.html, fill the "Actual" section on each ticket tab from that run: which agents worked, every delegation in order, which MCP tools each agent called, the requests and tokens, and the human approval. Keep my Expected section exactly as it is, side by side or right above, so the two can be compared.
2. Fill the Cash tab: starting checking balance $3,400.00 after the reset. Then for each ticket: what changed and why (101: approved payment #1, $840.00 to Bulldog Print Co for invoice 501. 102: approved payment #2, $2,400.00 rent to Elm City Properties for lease 1. 103: no cash change, discount only). Ending balance: read it from cash_accounts in data/campus_customs_new.db and show it equals 3,400 − 840 − 2,400 = 160.00. Also list the two rows in the payments table.
3. Write output/resolved_tickets.json: for each ticket, id, final status, short outcome, what each agent contributed, human approvals (payment id, payee, amount, approved_by), and the customer draft reply if there is one.
4. Write output/resolved_board.html, a page that opens by double-click and shows my three screenshots in output/resolved_board_images/ (ticket_101.png, ticket_102.png, ticket_103.png) with relative paths and a caption for each.
5. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard and the safety rules. Add a short "Final run" section with the three run ids and the cash result.

Log this prompt under Problem 9 in AI_prompts.md.
```

### Follow-up

_(none yet)_

---

## Problem 10: Reflection

### Prompt I typed

```text
Put my reflection into the Reflection tab of output/desk_tickets.html exactly as I wrote it below, one heading per question. Don't rewrite my answers or change any other tab or either database. 
Log this prompt under Problem 10 in AI_prompts.md.

1. How did the agents do on each ticket?

101 (tee, size S): Pretty good. Inventory caught that S was at 0 and offered M/L/XL. Accounting used the desk date to see invoice 501 was 3 days late and set up the $840 for me to approve. Two misses: the customer reply was written before I approved, so it tells Tauhid the reprint is still "on hold", and nobody actually ordered the reprint because there's no tool for it.

102 (rent): Best run. Facilities checked the notice against the lease ($2,400, due 9/2, 2 days out), Accounting set up the payment, I approved it. Only 14 requests and no wasted agents.

103 (20 hoodies for Yale AI Club): The discount math was right, $49.30 each, $986 total, still above the $22 cost. But Accounting never checked cash, and the reply promised to reprint the other 12. That's about $264 and we only had $160 left. It also didn't offer size L, which had 14 in stock.

2. Actual vs. Expected

101: Close, but Inventory handed the reply to Customer Service instead of Boss doing it at the end. That's why the reply went out too early.

102: Exactly what I planned.

103: I expected Accounting to flag the cash problem on a restock. It didn't check cash at all. Cash still ended at $160 like I planned, but only because no agent is able to buy anything.

3. What would be simpler as one agent?

Rent (102). It's just read the lease, check cash, set up the payment. One agent with three tools could do it in about 5 requests instead of 14. The team used 48 requests and about 66k tokens across all three tickets. The split only really paid off on 101, where stock, a late bill and a customer were all involved.

4. Three problems this team can already handle

- A customer wants the Crest Mug (0 in stock): check stock, find Elm City Gifts (3-day lead), reply honestly.
- Another overdue vendor invoice: same flow as 101, prepared for a human to approve.
- Another club wants a bulk deal on caps: 15% off $22 is $18.70, still well above the $6 cost.

5. Three problems it can't handle, and what I'd add

- Actually ordering stock. No order tool, so the reprints in 101 and 103 never happened. Add a Procurement agent with a purchase-order tool that checks cash first.
- Planning cash. We dropped to $160 and nothing warned us before promises were made. Add a Finance agent with a cash forecast.
- Billing customers. Yale AI Club would owe $986 but we can't invoice them or record payment. Add a Sales agent with invoice and payment tools.
Also: after rent was paid the lease still says due 9/2. Facilities needs a tool to roll it forward.
```

### Follow-up

_(none yet)_

---

## Problem 11: Submit to GitHub

### Prompt I typed

```text
Get Homework 5 ready to submit to a public GitHub repo called mgt409-hw5.

1. Write README.md in this project: what the project is (Campus Customs ops desk: five PydanticAI agents on gpt-6-luna, a FastMCP server over SQLite, a FastAPI backend and a React board, with humans approving every payment), then how to run it:
   - copy .env.example to .env and add a PORTKEY_API_KEY
   - python3 -m venv .venv and pip install -r requirements.txt
   - to start a clean run, copy data/campus_customs.db over data/campus_customs_new.db (or press Reset desk on the board)
   - the MCP server is started automatically by the backend, and by Claude Code through .mcp.json; it can also be run by hand with .venv/bin/python mcp_server/server.py
   - backend: cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000
   - board: cd frontend && npm install && npm run dev, then open http://localhost:5173
   - reset the database before a full three-ticket run
   Mention that data/campus_customs_new.db is committed in its final state after my run (cash $160, all three tickets resolved), and that output/ has the harness, plan, cash, reflection and screenshots.
2. Write output/github_url.txt containing only: https://github.com/Uncle-zoom/mgt409-hw5
3. Make a new folder next to this project: ../mgt409-hw5/hw5/. Copy this whole project into it, EXCEPT .env, .venv/, node_modules/, frontend/dist/, __pycache__/, .DS_Store files and data.zip. Both .db files in data/ MUST be copied. Don't change any file in the copy.
4. In ../mgt409-hw5, run git init with branch main, add everything, and commit with the message "MGT 409 Homework 5: Campus Customs multi-agent ops desk". Don't push yet.
5. Show me: the list of committed files, and confirm .env is not in it and both .db files are.

Do NOT change either database in this project. 
Log this prompt under Problem 11 in AI_prompts.md (before you copy, so the log is in the repo).
```

### Follow-up

_(none yet)_
