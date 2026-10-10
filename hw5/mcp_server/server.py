"""Campus Customs MCP server (stdio).

Tools over data/campus_customs_new.db, the working copy of the shop database.
Reading tools open the file read-only. The three writing tools (prepare_payment,
update_ticket_status, record_customer_reply) use a guarded connection that can only
write to pending_payments, customer_replies, ticket_status_log and tickets.status.
The agent tools cannot change cash_accounts or payments. Only the admin tools (started with
--admin, used by the dashboard's human approve/reject buttons) can, and no agent gets them.
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

mcp = FastMCP("campus-customs", log_level="WARNING")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def check_stock(sku: str, size: str) -> dict:
    """Check inventory for one SKU and size, plus every other size of that SKU.

    Use this when a customer order needs a specific size (e.g. ticket 101, a
    CC-TEE-WHITE size S) and you must know whether it is in stock and, if not,
    which other sizes are available. Reads the inventory table only.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid",
            (sku,),
        ).fetchall()
    if not rows:
        return {"found": False, "message": f"No inventory rows for sku '{sku}'."}
    requested = next((r for r in rows if r["size"] == size), None)
    others = [
        {"size": r["size"], "qty": r["qty"], "location": r["location"]}
        for r in rows
        if r["size"] != size
    ]
    if requested is None:
        return {
            "found": False,
            "message": f"SKU '{sku}' exists but has no size '{size}'.",
            "sku": sku,
            "name": rows[0]["name"],
            "other_sizes": others,
        }
    return {
        "found": True,
        "sku": sku,
        "name": requested["name"],
        "size": requested["size"],
        "qty": requested["qty"],
        "location": requested["location"],
        "other_sizes": others,
    }


@mcp.tool()
def get_lease(lease_id: int) -> dict:
    """Look up a lease and how many days remain until its rent is due.

    Use this when a rent notice or landlord email arrives (e.g. ticket 102) and
    you need the amount, landlord and due date. Days are counted from
    desk.date_today, not the real clock. Reads the leases and desk tables.
    """
    with _connect() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        desk = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if lease is None:
        return {"found": False, "message": f"No lease with id {lease_id}."}
    if desk is None:
        return {
            "found": True,
            "lease": dict(lease),
            "date_today": None,
            "days_until_due": None,
            "message": "desk table has no date_today, so days until due cannot be computed.",
        }
    today = date.fromisoformat(desk["date_today"])
    days = (date.fromisoformat(lease["next_due"]) - today).days
    return {
        "found": True,
        "lease": dict(lease),
        "date_today": desk["date_today"],
        "days_until_due": days,
    }


@mcp.tool()
def get_pricing(sku: str) -> dict:
    """Get unit cost, list price and margin per unit for a SKU.

    Use this when a customer asks for a discount or bulk price (e.g. ticket 103)
    so any offer can be checked against cost. Margin per unit is
    list_price - unit_cost. Reads the pricing table only.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    if row is None:
        return {"found": False, "message": f"No pricing row for sku '{sku}'."}
    return {
        "found": True,
        "sku": row["sku"],
        "unit_cost": row["unit_cost"],
        "list_price": row["list_price"],
        "margin_per_unit": round(row["list_price"] - row["unit_cost"], 2),
    }


# ---------------------------------------------------------------------------
# Ticket-desk tools (added in Problem 5)
# ---------------------------------------------------------------------------

TICKET_STATUSES = ("open", "awaiting_approval", "resolved")
PAYMENT_KINDS = ("invoice", "rent")

_WRITE_TABLES = {"pending_payments", "customer_replies", "ticket_status_log"}
_SCHEMA_TABLES = {"sqlite_master", "sqlite_temp_master"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pending_payments (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    kind TEXT NOT NULL,
    ref_id INTEGER NOT NULL,
    payee TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT,
    prepared_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_on TEXT NOT NULL,
    approved_by TEXT,
    decided_on TEXT
);
CREATE TABLE IF NOT EXISTS customer_replies (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_on TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_status_log (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    status TEXT NOT NULL,
    note TEXT,
    changed_on TEXT NOT NULL
);
"""


def _authorizer(action, arg1, arg2, dbname, source):
    """Allow reads, inserts into our own tables, and tickets.status updates. Deny the rest.

    This is what guarantees no tool can touch cash_accounts or payments, even by mistake.
    """
    if action in (sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION,
                  sqlite3.SQLITE_RECURSIVE, sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_INSERT and (arg1 in _WRITE_TABLES or arg1 in _SCHEMA_TABLES):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_UPDATE and (
        (arg1 == "tickets" and arg2 == "status") or arg1 in _SCHEMA_TABLES
    ):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_CREATE_TABLE and arg1 in _WRITE_TABLES:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _prepare_schema(conn: sqlite3.Connection) -> None:
    """Create our three tables if missing. Runs before an authorizer is attached."""
    conn.executescript(_SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(pending_payments)")}
    for col in ("approved_by", "decided_on"):  # tables made by an earlier version lack these
        if col not in cols:
            conn.execute(f"ALTER TABLE pending_payments ADD COLUMN {col} TEXT")


def _connect_write() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    _prepare_schema(conn)
    conn.set_authorizer(_authorizer)
    return conn


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone() is not None


def _desk_date(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return row["date_today"] if row else None


def _pending_total(conn: sqlite3.Connection) -> float:
    if not _table_exists(conn, "pending_payments"):
        return 0.0
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM pending_payments WHERE status = 'pending'"
    ).fetchone()
    return round(row["total"], 2)


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Read one support ticket (type, requester, subject, sku, size, qty, references, status).

    Use this first when you are handed a ticket id and need to know what the ticket
    says. Reads the tickets table only.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        return {"found": False, "message": f"No ticket with id {ticket_id}."}
    return {"found": True, "ticket": dict(row)}


@mcp.tool()
def get_desk_date() -> dict:
    """Get the shop's "today" (desk.date_today) and any desk notes.

    Use this whenever a date matters (overdue invoices, rent due dates). Never use
    the real clock. Reads the desk table only.
    """
    with _connect() as conn:
        row = conn.execute("SELECT date_today, notes FROM desk LIMIT 1").fetchone()
    if row is None:
        return {"found": False, "message": "The desk table has no row."}
    return {"found": True, "date_today": row["date_today"], "notes": row["notes"]}


@mcp.tool()
def get_invoice(invoice_id: int) -> dict:
    """Look up a vendor invoice, its vendor, and how many days overdue it is.

    Use this when a ticket references an invoice (e.g. ticket 101, invoice 501) or
    before preparing a vendor payment. Days overdue are counted from desk.date_today
    (0 when not yet due). Reads invoices, vendors and desk.
    """
    with _connect() as conn:
        inv = conn.execute(
            "SELECT i.id, i.vendor_id, v.name AS vendor_name, v.specialty AS vendor_specialty, "
            "v.lead_days AS vendor_lead_days, i.amount, i.due_date, i.status, i.description "
            "FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        today = _desk_date(conn)
    if inv is None:
        return {"found": False, "message": f"No invoice with id {invoice_id}."}
    result = {"found": True, "invoice": dict(inv), "date_today": today}
    if today is None:
        result["days_overdue"] = None
        result["message"] = "desk table has no date_today, so days overdue cannot be computed."
    else:
        late = (date.fromisoformat(today) - date.fromisoformat(inv["due_date"])).days
        result["days_overdue"] = max(late, 0)
        result["is_overdue"] = late > 0
    return result


@mcp.tool()
def get_cash_balance() -> dict:
    """Get the cash account balance(s), plus payments already waiting for human approval.

    Use this BEFORE preparing any payment, to check checking can cover it. The result
    includes pending_payments_total and balance_after_pending so you can see what is
    left once the requests already waiting are paid. Reads cash_accounts and pending_payments.
    """
    with _connect() as conn:
        rows = conn.execute("SELECT name, balance, date FROM cash_accounts ORDER BY name").fetchall()
        pending = _pending_total(conn)
    if not rows:
        return {"found": False, "message": "No cash accounts."}
    accounts = []
    for r in rows:
        acct = dict(r)
        if r["name"] == "checking":
            acct["balance_after_pending"] = round(r["balance"] - pending, 2)
        accounts.append(acct)
    return {"found": True, "accounts": accounts, "pending_payments_total": pending}


@mcp.tool()
def list_vendors() -> dict:
    """List vendors with their specialty and lead time in days.

    Use this to find who can restock or reprint an item and how long it takes
    (e.g. Bulldog Print Co does apparel reprints). Reads the vendors table only.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors ORDER BY id"
        ).fetchall()
    if not rows:
        return {"found": False, "message": "No vendors."}
    return {"found": True, "vendors": [dict(r) for r in rows]}


@mcp.tool()
def prepare_payment(
    ticket_id: int,
    kind: str,
    ref_id: int,
    payee: str,
    amount: float,
    reason: str,
    prepared_by: str,
) -> dict:
    """Prepare a payment request for a human to approve. It never moves money.

    Use this (accounting only) after checking the invoice or lease and the cash
    balance. kind is "invoice" (ref_id = invoices.id) or "rent" (ref_id = leases.id).
    The amount must equal the amount owed, and checking must still cover it after the
    payments already pending. Writes one row with status 'pending' to pending_payments;
    cash_accounts and payments are never touched. Asking again for the same kind and
    ref_id returns the existing pending request.
    """
    if kind not in PAYMENT_KINDS:
        return {"prepared": False, "message": f"kind must be one of {list(PAYMENT_KINDS)}."}
    if not payee.strip() or not prepared_by.strip():
        return {"prepared": False, "message": "payee and prepared_by are required."}
    if not (amount > 0):
        return {"prepared": False, "message": "amount must be greater than 0."}
    amount = round(amount, 2)
    with _connect_write() as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"prepared": False, "message": f"No ticket with id {ticket_id}."}
        if kind == "invoice":
            owed_row = conn.execute(
                "SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)
            ).fetchone()
            if owed_row is None:
                return {"prepared": False, "message": f"No invoice with id {ref_id}."}
            if owed_row["status"] != "open":
                return {"prepared": False,
                        "message": f"Invoice {ref_id} is '{owed_row['status']}', not open."}
            owed = owed_row["amount"]
        else:
            owed_row = conn.execute(
                "SELECT monthly_rent FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if owed_row is None:
                return {"prepared": False, "message": f"No lease with id {ref_id}."}
            owed = owed_row["monthly_rent"]
        if abs(owed - amount) > 0.005:
            return {"prepared": False,
                    "message": f"amount {amount} does not match the amount owed {owed}."}
        existing = conn.execute(
            "SELECT * FROM pending_payments WHERE kind = ? AND ref_id = ? AND status = 'pending'",
            (kind, ref_id),
        ).fetchone()
        if existing is not None:
            return {"prepared": True, "already_pending": True, "payment_request": dict(existing)}
        cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()
        if cash is None:
            return {"prepared": False, "message": "No checking account found."}
        pending = _pending_total(conn)
        available = round(cash["balance"] - pending, 2)
        if amount > available:
            return {"prepared": False,
                    "message": (f"Checking cannot cover {amount}: balance {cash['balance']}, "
                                f"pending {pending}, available {available}.")}
        today = _desk_date(conn)
        cur = conn.execute(
            "INSERT INTO pending_payments (ticket_id, kind, ref_id, payee, amount, reason, "
            "prepared_by, status, created_on) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (ticket_id, kind, ref_id, payee.strip(), amount, reason, prepared_by.strip(), today),
        )
        row = conn.execute("SELECT * FROM pending_payments WHERE id = ?", (cur.lastrowid,)).fetchone()
        return {
            "prepared": True,
            "already_pending": False,
            "payment_request": dict(row),
            "balance_after_pending": round(available - amount, 2),
            "note": "Pending only. A human must approve it on the board. No money has moved.",
        }


@mcp.tool()
def list_pending_payments(ticket_id: int) -> dict:
    """List the payments waiting for human approval on one ticket.

    Use this (boss) before setting a ticket's status, so the summary can name each
    pending payment's payee and amount. Reads the pending_payments table only.
    """
    with _connect() as conn:
        if not _table_exists(conn, "pending_payments"):
            rows = []
        else:
            rows = conn.execute(
                "SELECT id, ticket_id, kind, ref_id, payee, amount, reason, prepared_by, status "
                "FROM pending_payments WHERE ticket_id = ? AND status = 'pending' ORDER BY id",
                (ticket_id,),
            ).fetchall()
    payments = [dict(r) for r in rows]
    return {
        "found": True,
        "ticket_id": ticket_id,
        "pending_payments": payments,
        "pending_total": round(sum(p["amount"] for p in payments), 2),
        "message": None if payments else f"No pending payments for ticket {ticket_id}.",
    }


@mcp.tool()
def update_ticket_status(ticket_id: int, status: str, note: str = "") -> dict:
    """Set a ticket's status to open, awaiting_approval or resolved.

    Use this (boss only) when the work on a ticket is done: awaiting_approval if a
    payment is waiting for a human, otherwise resolved. "resolved" is refused while the
    ticket still has a pending payment. Updates tickets.status and logs the note in
    ticket_status_log.
    """
    if status not in TICKET_STATUSES:
        return {"updated": False, "message": f"status must be one of {list(TICKET_STATUSES)}."}
    with _connect_write() as conn:
        ticket = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"updated": False, "message": f"No ticket with id {ticket_id}."}
        if status == "resolved":
            waiting = conn.execute(
                "SELECT id, kind, amount FROM pending_payments "
                "WHERE ticket_id = ? AND status = 'pending'",
                (ticket_id,),
            ).fetchall()
            if waiting:
                return {
                    "updated": False,
                    "message": "Cannot resolve: this ticket still has a pending payment. "
                               "Use awaiting_approval until a human approves it.",
                    "pending_payments": [dict(w) for w in waiting],
                }
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.execute(
            "INSERT INTO ticket_status_log (ticket_id, status, note, changed_on) VALUES (?, ?, ?, ?)",
            (ticket_id, status, note, _desk_date(conn)),
        )
    return {"updated": True, "ticket_id": ticket_id,
            "previous_status": ticket["status"], "status": status}


@mcp.tool()
def record_customer_reply(ticket_id: int, message: str) -> dict:
    """Save a DRAFT reply to the customer. Nothing is sent.

    Use this (customer_service only) once the message is final and every fact in it was
    confirmed by another agent. Writes one row with status 'draft' to customer_replies.
    """
    if not message.strip():
        return {"saved": False, "message": "message is empty."}
    with _connect_write() as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"saved": False, "message": f"No ticket with id {ticket_id}."}
        cur = conn.execute(
            "INSERT INTO customer_replies (ticket_id, message, status, created_on) "
            "VALUES (?, ?, 'draft', ?)",
            (ticket_id, message, _desk_date(conn)),
        )
    return {"saved": True, "reply_id": cur.lastrowid, "status": "draft",
            "note": "Draft saved. Nothing was sent to the customer."}



# ---------------------------------------------------------------------------
# Admin tools for the dashboard (added in Problem 7)
#
# These move money, so NO agent gets them. They are only registered when the server is
# started with --admin, which only the dashboard backend (human approve/reject clicks)
# does. The agent team starts the server without --admin and also filters its tool list.
# They use their own guarded connection, separate from the agent tools' guard.
# ---------------------------------------------------------------------------

ADMIN = "--admin" in sys.argv[1:]

_ADMIN_UPDATES = {
    "cash_accounts": {"balance"},
    "pending_payments": {"status", "approved_by", "decided_on"},
    "invoices": {"status"},
    "tickets": {"status"},
}
_ADMIN_INSERTS = {"payments", "ticket_status_log"}


def _admin_authorizer(action, arg1, arg2, dbname, source):
    """Allow reads plus only the writes approve_payment and reject_payment need."""
    if action in (sqlite3.SQLITE_READ, sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION,
                  sqlite3.SQLITE_RECURSIVE, sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_INSERT and arg1 in _ADMIN_INSERTS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_UPDATE and arg2 in _ADMIN_UPDATES.get(arg1, ()):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _connect_admin() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)  # we manage the transaction
    conn.row_factory = sqlite3.Row
    _prepare_schema(conn)
    conn.set_authorizer(_admin_authorizer)
    return conn


def list_tickets() -> dict:
    """List every ticket with its id, type, requester, subject and status.

    For the dashboard only. Reads the tickets table.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, type, requester, subject, status FROM tickets ORDER BY id"
        ).fetchall()
    return {"found": bool(rows), "tickets": [dict(r) for r in rows]}


def list_all_pending_payments() -> dict:
    """List every payment still waiting for human approval, across all tickets.

    For the dashboard only. Reads the pending_payments table.
    """
    with _connect() as conn:
        if not _table_exists(conn, "pending_payments"):
            rows = []
        else:
            rows = conn.execute(
                "SELECT id, ticket_id, kind, ref_id, payee, amount, reason, prepared_by, status, "
                "created_on FROM pending_payments WHERE status = 'pending' ORDER BY id"
            ).fetchall()
    payments = [dict(r) for r in rows]
    return {"found": True, "pending_payments": payments,
            "pending_total": round(sum(p["amount"] for p in payments), 2)}


def approve_payment(payment_id: int, approved_by: str) -> dict:
    """Approve one pending payment and pay it. Human approval only, never an agent.

    In one transaction: subtract the amount from checking, insert a row in payments,
    mark the pending payment approved, mark the invoice paid (for an invoice payment),
    and set the ticket to resolved if it has no other pending payment. Fails if the
    payment is not pending (so approving twice fails) or checking can't cover it.
    """
    if not approved_by.strip():
        return {"approved": False, "message": "approved_by is required."}
    conn = _connect_admin()
    try:
        conn.execute("BEGIN IMMEDIATE")
        pay = conn.execute("SELECT * FROM pending_payments WHERE id = ?", (payment_id,)).fetchone()
        if pay is None:
            conn.execute("ROLLBACK")
            return {"approved": False, "message": f"No pending payment with id {payment_id}."}
        if pay["status"] != "pending":
            conn.execute("ROLLBACK")
            return {"approved": False,
                    "message": f"Payment {payment_id} is already {pay['status']}, not pending."}
        cash = conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()
        if cash is None or cash["balance"] < pay["amount"]:
            conn.execute("ROLLBACK")
            have = None if cash is None else cash["balance"]
            return {"approved": False,
                    "message": f"Checking cannot cover {pay['amount']} (balance {have})."}
        today = _desk_date(conn)
        new_balance = round(cash["balance"] - pay["amount"], 2)
        conn.execute("UPDATE cash_accounts SET balance = ? WHERE name = 'checking'", (new_balance,))
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, 'checking', ?, ?)",
            (pay["kind"], pay["ref_id"], pay["amount"], today, approved_by.strip()),
        )
        marked = conn.execute(
            "UPDATE pending_payments SET status = 'approved', approved_by = ?, decided_on = ? "
            "WHERE id = ? AND status = 'pending'",
            (approved_by.strip(), today, payment_id),
        )
        if marked.rowcount != 1:
            conn.execute("ROLLBACK")
            return {"approved": False, "message": f"Payment {payment_id} is no longer pending."}
        invoice_status = None
        if pay["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (pay["ref_id"],))
            invoice_status = "paid"
        others = conn.execute(
            "SELECT COUNT(*) AS n FROM pending_payments WHERE ticket_id = ? AND status = 'pending'",
            (pay["ticket_id"],),
        ).fetchone()["n"]
        ticket_status = None
        if others == 0:
            conn.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (pay["ticket_id"],))
            conn.execute(
                "INSERT INTO ticket_status_log (ticket_id, status, note, changed_on) "
                "VALUES (?, 'resolved', ?, ?)",
                (pay["ticket_id"], f"Payment {payment_id} approved by {approved_by.strip()}.", today),
            )
            ticket_status = "resolved"
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {
        "approved": True,
        "payment_id": payment_id,
        "payments_row_id": cur.lastrowid,
        "ticket_id": pay["ticket_id"],
        "amount": pay["amount"],
        "payee": pay["payee"],
        "new_checking_balance": new_balance,
        "invoice_status": invoice_status,
        "ticket_status": ticket_status,
    }


def reject_payment(payment_id: int) -> dict:
    """Reject one pending payment. Human only, never an agent. Cash is never touched.

    Marks the pending payment rejected. Fails if it is not pending.
    """
    conn = _connect_admin()
    try:
        conn.execute("BEGIN IMMEDIATE")
        today = _desk_date(conn)
        done = conn.execute(
            "UPDATE pending_payments SET status = 'rejected', decided_on = ? "
            "WHERE id = ? AND status = 'pending'",
            (today, payment_id),
        )
        if done.rowcount != 1:
            row = conn.execute("SELECT status FROM pending_payments WHERE id = ?", (payment_id,)).fetchone()
            conn.execute("ROLLBACK")
            if row is None:
                return {"rejected": False, "message": f"No pending payment with id {payment_id}."}
            return {"rejected": False,
                    "message": f"Payment {payment_id} is already {row['status']}, not pending."}
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {"rejected": True, "payment_id": payment_id}


if ADMIN:
    for _tool in (list_tickets, list_all_pending_payments, approve_payment, reject_payment):
        mcp.tool()(_tool)


if __name__ == "__main__":
    mcp.run(transport="stdio")
