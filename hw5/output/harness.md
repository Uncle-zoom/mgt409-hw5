# Campus Customs Ops Desk: Agent Harness

## Database

Source: `data/campus_customs.db` (read-only original, never modified). Working copy that the agents and the dashboard change: `data/campus_customs_new.db` (a byte-identical copy of the original, SHA-256 `23686a90…f360a`, until the first run). The tables below describe the original. What the final run changed in the working copy is in "Final run" at the end.

The database has 9 tables and three declared foreign keys: `tickets.lease_id` → `leases(id)`, `tickets.invoice_id` → `invoices(id)`, and `invoices.vendor_id` → `vendors(id)`. All other links (ticket `sku`/`size` to `inventory` and `pricing`, `payments.ref_id` to its target) are by convention only. "Today" for the desk is `2026-08-31`.

### tickets (3 rows)
Fields: `id` INTEGER PK, `type` TEXT, `requester` TEXT, `subject` TEXT, `sku` TEXT, `size` TEXT, `qty` INTEGER, `lease_id` INTEGER, `invoice_id` INTEGER, `status` TEXT, `notes` TEXT, `created_at` TEXT.
Why it matters: this is the work queue. All three tickets (101 customer_order, 102 rent_notice, 103 price_override) are `open`, and each one points into the other tables.

### desk (1 row)
Fields: `date_today` TEXT, `notes` TEXT.
Why it matters: the only source of "today" (`2026-08-31`). Every agent needs it to judge overdue or due-soon dates (invoice 501, lease 1). `notes` is NULL.

### inventory (10 rows)
Fields: `sku` TEXT (PK part), `name` TEXT, `size` TEXT (PK part), `qty` INTEGER, `location` TEXT. Primary key is (`sku`, `size`).
Why it matters: stock checks for ticket 101 (tee size S has 0) and ticket 103 (hoodie size M has 8, request is 20).

### pricing (4 rows)
Fields: `sku` TEXT PK, `unit_cost` REAL, `list_price` REAL.
Why it matters: margin math for the price-override ticket 103 (hoodie cost 22.00, list 58.00), and the selling price for ticket 101 (tee list 28.00).

### vendors (3 rows)
Fields: `id` INTEGER PK, `name` TEXT, `specialty` TEXT, `lead_days` INTEGER.
Why it matters: who can restock and how fast. Bulldog Print Co (apparel reprint, 5 days) is the vendor on invoice 501 and the likely source for apparel. QuickShip CT is a local courier (1 day). Elm City Gifts handles mugs and small goods, so no ticket needs it.

### leases (1 row)
Fields: `id` INTEGER PK, `space_name` TEXT, `landlord` TEXT, `monthly_rent` REAL, `next_due` TEXT, `notes` TEXT.
Why it matters: ticket 102. Rent of 2400.00 for the Chapel Street shop is due 2026-09-02.

### cash_accounts (1 row)
Fields: `name` TEXT PK, `balance` REAL, `date` TEXT.
Why it matters: the finance/payment agent must check funds before paying anything. One account, `checking`, with 3400.00 as of 2026-08-31.

### invoices (1 row)
Fields: `id` INTEGER PK, `vendor_id` INTEGER, `amount` REAL, `due_date` TEXT, `status` TEXT, `description` TEXT.
Why it matters: ticket 101 references invoice 501 (Bulldog Print Co, 840.00, due 2026-08-28, open), so it is 3 days overdue as of `date_today`.

### payments (0 rows)
Fields: `id` INTEGER PK, `kind` TEXT, `ref_id` INTEGER, `amount` REAL, `account` TEXT, `paid_at` TEXT, `approved_by` TEXT.
Why it matters: this is where the payment agent would record rent (ticket 102) and the invoice (ticket 101). It is empty in the original, so there is no payment history. After the final run the working copy has two rows (see "Final run").

## Ticket chains (what each ticket needs)

**Ticket 101, customer_order (Tauhid Zaman, tee size S, qty 1).** Links to `inventory` (`CC-TEE-WHITE` / S), `pricing` (`CC-TEE-WHITE`) and `invoices` (501), and through the invoice to `vendors` (1).
- Stock: `CC-TEE-WHITE` size S has qty 0. M has 5, L has 3, XL has 2.
- Price: cost 8.00, list 28.00.
- Invoice 501: vendor 1 (Bulldog Print Co, lead 5 days), 840.00, due 2026-08-28 (overdue by 3 days), status open, "Rush reprint CC-TEE-WHITE S".
- To resolve: size S can't be filled from stock. The agents need a reprint decision or a size substitution, and the open invoice 501 needs a payment decision.

**Ticket 102, rent_notice (Elm City Properties).** Links to `leases` (1), then `cash_accounts` and `payments`.
- Lease 1: Chapel Street shop, landlord Elm City Properties (matches the requester), 2400.00/month, next due 2026-09-02, which is 2 days after `date_today`, as the notice says.
- Cash: checking 3400.00.
- To resolve: pay 2400.00 before 2026-09-02 and record it in `payments`. That leaves 1000.00.

**Ticket 103, price_override (Yale AI Club, 20 hoodies size M).** Links to `inventory` (`CC-HOOD-NAVY` / M) and `pricing` (`CC-HOOD-NAVY`).
- Stock: size M has 8, so 12 are short. S has 4, L has 14, XL has 6.
- Price: cost 22.00, list 58.00, so a 36.00 margin per unit at list. 20 units at list is 1160.00.
- To resolve: a discount decision (how much, who approves) and a restock for the 12 missing units, probably through Bulldog Print Co.

## Things that look odd or missing

- **Cash is tight if everything is paid.** Rent 2400.00 plus invoice 501 at 840.00 is 3240.00 against 3400.00 in checking, leaving 160.00. Nothing is left for restocking the hoodies.
- **Invoice 501 amount looks large.** It is 840.00 for "Rush reprint CC-TEE-WHITE S", and the tee's unit cost is 8.00, which would be 105 units. The database doesn't say the quantity or whether the reprint was delivered, so I can't tell whether it is correct.
- **Invoice 501 already exists for the tee size S reprint**, yet S stock is 0. The data doesn't show whether that reprint arrived, is on order, or is unpaid, and there is no order or receiving table.
- **No discount rules.** No table holds a discount policy, approval threshold, or customer-tier info, so how much of a discount ticket 103 may get is not defined in the data.
- **No approval rules for payments.** `payments.approved_by` exists, but nothing says who may approve or up to what amount.
- **No vendor-to-SKU mapping, vendor price list or pricing.** Vendors only have a free-text specialty and a lead time, so the hoodie restock vendor is an inference.
- **Foreign keys cover only some links.** `tickets.sku`/`size`, `payments.ref_id` and `payments.account` have no declared foreign key, so nothing in the schema stops them from pointing at a missing row. All three tickets' references do resolve today.
- **`desk.notes` is NULL**, and `leases.notes` is NULL.
- **Timestamps mix formats.** Tickets use ISO datetimes with a `-04:00` offset, while `date_today`, due dates and `cash_accounts.date` are plain dates.
- **`payments` is empty and `QuickShip CT`, `Elm City Gifts`, the hat and the mug** aren't used by any open ticket (the mug has qty 0 and the hat 40).
- **Ticket 101's note** ("Needs a tee in size S.") doesn't say whether the customer would accept another size.

## Agents

Five PydanticAI agents (`backend/team.py`), each loading its own prompt file from `backend/prompts/` at startup. All use gpt-6-luna through Portkey. Each agent gets only the MCP tools in its prompt, plus `delegate(to_agent, task)`, which can call any other agent except itself.

| Agent | Role | Prompt file | MCP tools | Usual handoffs |
|---|---|---|---|---|
| boss | Desk manager. Reads the ticket, picks ONE specialist to start, writes the summary and sets the ticket status. | `boss.md` | `get_ticket`, `get_desk_date`, `list_pending_payments`, `update_ticket_status` | customer_order → inventory, rent_notice → facilities, price_override → accounting |
| inventory | Stock and restock. Checks sizes and vendor lead times. | `inventory.md` | `check_stock`, `list_vendors` | → accounting (anything that costs money or an unpaid vendor invoice), → customer_service (to reply to the customer) |
| accounting | Invoices, cash and pricing. Prepares payments for a human to approve and sets discount prices. | `accounting.md` | `get_invoice`, `get_cash_balance`, `get_pricing`, `get_desk_date`, `prepare_payment` | → inventory (stock questions), → customer_service (the approved price or the reply) |
| facilities | The Chapel Street lease and rent schedule. Checks a notice against the lease. | `facilities.md` | `get_lease`, `get_desk_date` | → accounting (to prepare the rent payment once the notice checks out) |
| customer_service | Writes the customer reply and saves it as a draft. | `customer_service.md` | `get_ticket`, `record_customer_reply` | none usually; asks the agent who owns a missing fact |

Paths taken in the final run (handoffs in the order they started):
- **101 tee size S:** boss → inventory, inventory → accounting (invoice 501), inventory → customer_service.
- **102 rent:** boss → facilities, facilities → accounting (prepare the 2,400.00 rent payment).
- **103 hoodie discount:** boss → accounting, accounting → inventory (12 units short), accounting → customer_service.

Where a customer reply was needed (101 and 103), the specialist handed to customer_service itself rather than boss doing it, and the work came back to boss through the chain. `output/desk_tickets.html` compares these paths with the plan.

## MCP Tools

Server: `campus-customs` (`mcp_server/server.py`, FastMCP over stdio). It works on `data/campus_customs_new.db`, with the path built from the location of `server.py`. Read tools open the file read-only. The three write tools use a guarded connection (see Safety and Limits). Every tool uses parameterized SQL, returns only values found in the database, and returns a clear not-found or refusal message.

| Tool | Table(s) it uses | Used by | What it does |
|---|---|---|---|
| `check_stock(sku, size)` | `inventory` | inventory | Qty and location for one size plus every other size of the SKU. |
| `get_lease(lease_id)` | `leases`, `desk` | facilities | Lease row, `date_today` and days until `next_due`. |
| `get_pricing(sku)` | `pricing` | accounting | `unit_cost`, `list_price` and margin per unit. |
| `get_ticket(ticket_id)` | `tickets` | boss, customer_service | The ticket row. |
| `get_desk_date()` | `desk` | boss, accounting, facilities | `date_today` and desk notes. |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | accounting | Invoice plus vendor, with days overdue counted from `date_today`. |
| `get_cash_balance()` | `cash_accounts`, `pending_payments` | accounting | Account balance plus the total of pending payments and the balance after them. |
| `list_vendors()` | `vendors` | inventory | Vendors with specialty and `lead_days`. |
| `prepare_payment(ticket_id, kind, ref_id, payee, amount, reason, prepared_by)` | writes `pending_payments` (reads `tickets`, `invoices`, `leases`, `cash_accounts`) | accounting | Creates a payment request with status `pending`. Never touches `cash_accounts` or `payments`. |
| `list_pending_payments(ticket_id)` | `pending_payments` | boss | The payments waiting for human approval on one ticket (payee, amount), plus their total. |
| `update_ticket_status(ticket_id, status, note)` | writes `tickets.status` and `ticket_status_log` (reads `pending_payments`) | boss | Sets `open`, `awaiting_approval` or `resolved`. Refuses `resolved` while the ticket has a pending payment. |
| `record_customer_reply(ticket_id, message)` | writes `customer_replies` | customer_service | Saves a draft reply. Nothing is sent. |
| `list_tickets()` | `tickets` | dashboard only | Every ticket with id, type, requester, subject and status. |
| `list_all_pending_payments()` | `pending_payments` | dashboard only | Every payment still waiting for approval, across all tickets. |
| `approve_payment(payment_id, approved_by)` | writes `cash_accounts`, `payments`, `pending_payments`, `invoices`, `tickets` | dashboard only (human click) | Pays one pending payment in a single transaction. Fails if it isn't pending. |
| `reject_payment(payment_id)` | writes `pending_payments` | dashboard only (human click) | Marks a pending payment rejected. Never touches cash. |

The first three tools are the Problem 3 tools and are unchanged. What they unlock, with the real numbers:
- **`check_stock` unlocks ticket 101.** Size S of `CC-TEE-WHITE` has qty 0 in Aisle B, and the tool also shows the other sizes (M 5, L 3, XL 2) that can be offered instead.
- **`get_lease` unlocks ticket 102.** It returns lease 1 (2,400.00, due 2026-09-02) and counts days from `desk.date_today` (2026-08-31), which gives 2 days.
- **`get_pricing` unlocks ticket 103.** For `CC-HOOD-NAVY` it returns cost 22.00, list 58.00 and a 36.00 margin, so any discount can be checked against cost.

The last four tools are admin tools for the dashboard. No agent has them (see Safety and Limits).

Tables the tools create when first needed: `pending_payments`, `customer_replies` and `ticket_status_log`. `ticket_status_log` was not in the brief. It holds the `note` from `update_ticket_status`, so the original `tickets.notes` text is never edited.

## API Routes

FastAPI app in `backend/main.py`, started with `cd backend && uvicorn main:app --reload --port 8000`. CORS allows `http://localhost:5173`. All shop data goes through the campus-customs MCP server (started with `--admin` by `backend/shop.py`), with no database code in `backend/`.

- `GET /health`: returns `{"status": "ok"}`.
- `GET /api/tickets`: the three tickets with id, type, requester, subject and status.
- `POST /api/tickets/{ticket_id}/run`: starts the agent team on that ticket in the background and returns a `run_id` right away. Returns 409 if a run is already going and 404 for an unknown ticket.
- `GET /api/events?run_id=...&after=N`: that run's events in order (agent, step type, tool or delegation target, short text) read from the audit trail, only those after the first N. Also says whether the run is finished and gives its final summary.
- `GET /api/approvals`: payments waiting for a human, with their total.
- `POST /api/approvals/{payment_id}/approve`: approves and pays one pending payment (body `{"approved_by": "..."}` is optional). Returns 409 if it isn't pending, so approving twice fails.
- `POST /api/approvals/{payment_id}/reject`: rejects one pending payment. Cash is never touched.
- `GET /api/cash`: the checking balance, the pending total and the balance after pending.
- `POST /api/reset`: refuses with 409 while a run is going. Copies `data/campus_customs.db` over `data/campus_customs_new.db` and clears the in-memory run state. It never touches `output/audit_trail.json`.

Only one agent run can be active at a time. Run state lives in memory, so after a server restart `GET /api/events` can still replay a run from the audit trail but has no final summary for it.

## Dashboard

React + Vite + TypeScript app in `frontend/`, built like an airport departures board: tickets are flights whose status flips, each agent has its own gate (lane) with its own color and icon, and checking cash is a scoreboard. It uses the API routes above and nothing else.

- **Tickets:** the three tickets with their status, and a Run button for the selected one (disabled while a run is going).
- **Gates:** while a run goes, the page polls `GET /api/events` every second and shows each agent's messages, tool calls and handoffs (as `Boss → Inventory` chips) in its own lane.
- **Run summary:** when the run finishes, one card per agent that took part with what it found, what it did and the tools it used, and the ticket's new status.
- **Approvals and cash:** payments waiting for approval show as cards with Approve and Reject, each with an in-page "Are you sure?". Checking is shown big, with the after-pending amount, and counts down after an approval.
- **Reset desk:** an in-page confirm, then `POST /api/reset`.

The layout, the look of each agent and the reasons for the choices are in `output/design.md`. To run it:

```bash
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000   # API
cd frontend && npm run dev                                        # dashboard on http://localhost:5173
```

## Safety and Limits

### Guardrails (real-business rules, enforced in code)
- **Agents never pay.** No MCP tool changes `cash_accounts` or `payments`. The write connection has a SQLite authorizer that only allows inserts into `pending_payments`, `customer_replies` and `ticket_status_log`, and updates to `tickets.status`. Anything else (including an update to `cash_accounts`) is denied by SQLite.
- **`prepare_payment` only creates a pending request.** It accepts `kind` `invoice` or `rent`, requires the amount to equal the amount owed (invoice amount or `monthly_rent`), requires the invoice to be open, and refuses if checking minus payments already pending can't cover it. Asking twice for the same kind and ref returns the existing request instead of a duplicate.
- **A ticket can't be closed with money waiting.** `update_ticket_status` refuses `resolved` while the ticket has a pending payment.
- **Customer replies are drafts.** `record_customer_reply` saves a draft and nothing is sent.
- **Least privilege.** Each agent only sees the MCP tools listed above for it, even though all of them share one server connection.
- **Today is the desk date.** Dates come from `desk.date_today`, never the real clock.
- **Original data is safe.** The agents only touch `data/campus_customs_new.db`. `data/campus_customs.db` is never opened by the server.
- **Model is locked.** `MODEL` in `.env` must be exactly `gpt-6-luna` and `PORTKEY_API_KEY` must be set, or the team refuses to start.

### Money only moves from a human click
- `approve_payment` (and `reject_payment`, `list_tickets`, `list_all_pending_payments`) are hidden from every agent. They are left out of every agent's tool list in `backend/team.py`, and `team.py` checks at import that no agent has one.
- The server only registers them when started with `--admin`. The agent team starts the server without that flag, so the agents' connection doesn't even list them.
- Only the dashboard backend starts the server with `--admin`, and only `POST /api/approvals/{payment_id}/approve` calls `approve_payment`, so money moves only from a human click on the board.
- The admin tools use their own guarded connection (separate from the agent tools' guard). SQLite only lets it update `cash_accounts.balance`, `pending_payments` (status, approved_by, decided_on), `invoices.status` and `tickets.status`, and insert into `payments` and `ticket_status_log`. Everything else, including deletes, is denied.
- `approve_payment` runs in one transaction: it subtracts the amount from checking, inserts the `payments` row, marks the pending payment approved, marks an invoice payment's invoice `paid`, and sets the ticket to `resolved` if it has no other pending payment. It fails if the payment isn't pending, or if checking can't cover it, and nothing changes in that case.

### Limits (one config block, `backend/config.py`)
| Limit | Value | How it is enforced |
|---|---|---|
| Model requests per agent run | 8 | Counted per agent run. The run stops before the 9th request. |
| Total tokens per ticket | 100,000 | Usage is shared by every agent on the ticket and checked by PydanticAI after each model response, so one response can overshoot the limit before the run stops. |
| Time per model call | 60 seconds | Set on the client and the model settings. Retries are turned off so 60 seconds is the real cap. |
| Delegation depth | 3 | boss is depth 0, so a chain can reach depth 3 (for example boss → facilities → accounting → customer_service). A 4th handoff is blocked. |
| Repeated handoff | blocked | The same from → to handoff can't happen twice on one ticket. Delegating to yourself or to an unknown agent is also blocked. |

When a limit or a model error stops a run, `TicketRunResult.stopped_reason` says why and the stop is written to the audit trail.

### Audit trail (`output/audit_trail.json`)
- One JSON entry per model call, tool call and delegation (blocked handoffs too): timestamp, run_id, ticket_id, agent, step type, tool or target, short args, short result, tokens and stop reason.
- Entries are only appended. The file is never wiped, and if it can't be read as a JSON list the write fails instead of overwriting it.
- API keys, email addresses and a person's requester name are replaced before anything is written. The reply tool's arguments are stored as a length only, but an agent's own final message (shortened to 240 characters) can include the start of a draft reply. Organization names (Elm City Properties, Yale AI Club) are kept.

### Not enforced by code
- The **15% bulk-discount cap** and the "never price at or below cost" rule are in the accounting prompt only. No tool checks a discount price.
- **"Nothing ships against an unpaid invoice"** is a prompt rule. No tool tracks shipping or fulfilment. The only thing that marks an invoice paid is `approve_payment`, after a human approves.
- The **same-handoff block** is by agent pair, so a different task text to the same agent is also blocked.

## Final run

One clean run of each ticket on the dashboard, after a reset. These three runs are the only ones counted (earlier test runs are in the audit trail but ignored).

| Ticket | Run id | Agents (handoffs in order) | Model requests | Tokens | Human approval | Final status |
|---|---|---|---|---|---|---|
| 101 | `01a63e5fc065` | Boss → Inventory; Inventory → Accounting; Inventory → Customer Service | 18 | 27,065 | payment #1, $840.00 to Bulldog Print Co (invoice 501) | resolved |
| 102 | `4cc7c3ef82c3` | Boss → Facilities; Facilities → Accounting | 14 | 17,985 | payment #2, $2,400.00 to Elm City Properties (lease 1) | resolved |
| 103 | `1690588b0383` | Boss → Accounting; Accounting → Inventory; Accounting → Customer Service | 16 | 21,029 | none (discount only) | resolved |
| **Total** | | | **48** | **66,079** | | |

**Cash result.** Checking started at $3,400.00. Approved payment #1 took it to $2,560.00 and approved payment #2 to $160.00. Ticket 103 changed no cash. The `cash_accounts` row in `data/campus_customs_new.db` reads 160.0, which equals 3,400 − 840 − 2,400 = 160.00. The `payments` table has the two rows (invoice 501 for 840.00 and rent lease 1 for 2,400.00), both approved by `human (board)`, and invoice 501 is `paid`.

Other records in the working copy: two draft customer replies (tickets 101 and 103, nothing sent) and no pending payments. The original `data/campus_customs.db` was never changed.

Where to look:
- `output/desk_tickets.html`: the plan next to what actually happened for each ticket, and the cash ledger.
- `output/resolved_tickets.json`: final status, outcome, agent contributions, approvals and draft replies per ticket.
- `output/resolved_board.html`: screenshots of the dashboard after each run.
