# Campus Customs MCP server

An MCP server (FastMCP from `mcp` 1.x, stdio transport, server name `campus-customs`) that gives the Campus Customs ops-desk agents their only way to read and write shop data.

## Database

It works on `data/campus_customs_new.db`, the working copy of the shop database. The path is built from the location of `server.py`, so it works from any current folder. Reading tools open the file read-only (`mode=ro`). The original `data/campus_customs.db` is never used.

The three writing tools use a guarded connection: SQLite only allows inserts into `pending_payments`, `customer_replies` and `ticket_status_log` and updates to `tickets.status`. Nothing can change `cash_accounts` or `payments`. The three tables above are created on first use if missing.

## Tools

| Tool | Table(s) | Use it for |
|---|---|---|
| `check_stock(sku, size)` | `inventory` | Qty and location for one size, plus every other size of the SKU (ticket 101). |
| `get_lease(lease_id)` | `leases`, `desk` | Lease row, `date_today` and days until `next_due` (ticket 102). |
| `get_pricing(sku)` | `pricing` | `unit_cost`, `list_price` and margin per unit (ticket 103). |
| `get_ticket(ticket_id)` | `tickets` | Read one ticket. |
| `get_desk_date()` | `desk` | The shop's "today" (`date_today`) and desk notes. |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | Invoice, vendor and days overdue from `date_today`. |
| `get_cash_balance()` | `cash_accounts`, `pending_payments` | Balance, pending payments total and balance after pending. |
| `list_vendors()` | `vendors` | Vendors, specialty and `lead_days`. |
| `prepare_payment(ticket_id, kind, ref_id, payee, amount, reason, prepared_by)` | writes `pending_payments` | Prepare a payment request with status `pending` for a human to approve. Never moves money. |
| `list_pending_payments(ticket_id)` | `pending_payments` | Payments waiting for human approval on one ticket, with payee, amount and total. |
| `update_ticket_status(ticket_id, status, note)` | writes `tickets.status`, `ticket_status_log` | Set `open`, `awaiting_approval` or `resolved`. Refuses `resolved` while a payment is pending. |
| `record_customer_reply(ticket_id, message)` | writes `customer_replies` | Save a draft reply. Nothing is sent. |
| `list_tickets()` | `tickets` | Admin only. Every ticket with id, type, requester, subject and status. |
| `list_all_pending_payments()` | `pending_payments` | Admin only. Every payment waiting for approval. |
| `approve_payment(payment_id, approved_by)` | writes `cash_accounts`, `payments`, `pending_payments`, `invoices`, `tickets` | Admin only. Pays one pending payment in one transaction. Fails if it isn't pending. |
| `reject_payment(payment_id)` | writes `pending_payments` | Admin only. Marks a pending payment rejected. Never touches cash. |

Every tool uses parameterized SQL, returns only real database values, and returns `found: false` (or `prepared`/`updated`/`saved: false`) with a message when nothing matches or a rule refuses the action. The first three tools are unchanged from Problem 3.

## Admin tools

The last four tools move money or run the dashboard, so no agent gets them. They are only registered when the server is started with `--admin`, which only the dashboard backend (`backend/shop.py`) does. Without the flag (the agent team, and Claude Code through `.mcp.json`) they are not listed at all. They use their own guarded connection that only allows the writes those tools need.

## Run

```bash
.venv/bin/python mcp_server/server.py          # agent tools
.venv/bin/python mcp_server/server.py --admin  # agent tools plus the admin tools
```

The server speaks MCP over stdio, so it is normally started by an MCP client: Claude Code through `.mcp.json`, or the agent team in `backend/team.py`.
