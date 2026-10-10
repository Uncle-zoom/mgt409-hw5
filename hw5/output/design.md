# Campus Customs Ops Desk: Design

The dashboard (`frontend/`, React + Vite + TypeScript) is built to feel like an airport departures board. Each ticket is a flight, each agent is a gate, and cash is a scoreboard. It talks to the backend at `http://localhost:8000` and uses black with a hot-pink accent.

## Layout

A top bar holds the shop mark (CC), the title "Campus Customs Ops Desk", and a **Reset desk** button, with a strip of pink hazard tape under it. Below it is a two-column page:

**Left column, top to bottom**
1. **Departures board.** One row per ticket (from `GET /api/tickets`): flight number (`CC101`), type, who it's from, subject, and status. Clicking a row selects it. The selected row has a pink bar and a ▶ pointer. The board header shows the desk date (taken from the cash `as_of` date).
2. **Run bar.** The selected ticket, a live status line, and the big pink **Run ticket N** button. While a run is going the button reads "Run in progress…" and is disabled, and so is Reset desk.
3. **Gates.** Five lanes, one per agent (see below), filled in as the run happens.
4. **Run summary.** Appears only when a run has finished: a card per agent that took part.

**Right column (stays in view while you scroll)**
1. **Checking scoreboard.**
2. **Waiting for your OK.** The payment approval cards.

Under 1100px wide everything stacks in one column in this order: board, run bar, cash and approvals, gates, summary. The board rows re-flow into small cards on phones.

## How each agent looks

Every agent has its own color, gate letter, icon and role label, used everywhere that agent appears (lane, handoff chips, summary card, "prepared by" badge on a payment).

| Agent | Gate | Color | Icon | Role label |
|---|---|---|---|---|
| Boss | A | pink | clipboard with a check | Desk manager |
| Inventory | B | blue | stacked boxes | Stock and restock |
| Accounting | C | orange | coin | Invoices, cash and pricing |
| Facilities | D | lime | building | Lease and rent |
| Customer Service | E | violet | chat bubble | Customer replies |

Each lane has a colored left edge, a gate tag ("GATE C"), the icon, the name and role, and a status light: **STANDING BY** (dimmed, nothing yet), **WORKING** (glowing border, pulsing dot), **WAITING** (it handed work on and is waiting for the report), **DONE**.

Inside a lane, events slide in as the run polls `GET /api/events` every second, and the lane scrolls to the newest one:
- **Messages** from the agent are speech bubbles tinted with its color.
- **Tool calls** are a monospace chip with the tool name, the arguments, and the result (long text is cut to two lines with a "more" link).
- **"Decides to call …"** lines show what the model asked for before the tool ran.
- **Handoffs** are chips like **Boss → Inventory**, with each name in its own color. The chip shows in the lane that handed off ("handed off") and in the lane that received it ("picked up the task"). When the work comes back the caller's lane gets "report back from Inventory". The Gates header also shows the whole route of the run as a row of these chips.
- **Blocked handoffs** (a repeat, a self-call, or a depth limit) show in red with the reason.

The lane text comes from the audit trail, which keeps entries short, so long messages are cut off there. The full report from each agent is in the run summary.

## Tickets, resolved status and the summary

- **Status** is drawn with split-flap tiles: `OPEN` in white, `AWAITING APPROVAL` in yellow with a slow blink, `RESOLVED` in green. When a status changes, only the tiles whose letters changed flip. The row for the ticket being worked also shows a pulsing "working" marker.
- Statuses are re-read from the server when a run finishes and after every approve, reject or reset, so approving the last pending payment for a ticket flips it to RESOLVED on the board.
- When a run finishes, the Run bar says the ticket's new status and the page scrolls to the **Run summary**. Its header shows the status as a pill, then the agents in order (as a route of chips), the model request count, the tokens, and whether a human approval is needed and for how much. A run that stopped early or errored gets a red "did not finish cleanly" card with the reason.
- Each agent that took part gets a **summary card** with three parts: **What it found** (the agent's own final report), **What it did** (handoffs it made, payments it prepared with payee and amount, a draft reply saved, the status it set; or "Looked things up and reported back" when it changed nothing), and **Tools used** (chips, with ×N for repeats).

## Cash and approvals

- **Checking** is shown on a dark scoreboard in large digit tiles with the "as of" date. Under it, **Pending approval** (yellow) and **After pending** (pink) show what the balance would be once the waiting payments are paid. The digits are dimmed until the balance has loaded.
- After an approval, the balance counts down over about 1.3 seconds, the digits flash red and drop, and a red chip such as "−$2,400.00" floats down and fades. The pending and after-pending figures animate the same way.
- Each **payment card** shows the amount (large), the payee, the ticket, what it is for (for example "invoice #501"), a badge for the agent that prepared it, and the reason. It has **Approve** and **Reject** buttons.
- **"Are you sure?"** happens inside the card, with no browser popups: Approve turns the card into a confirmation ("This pays $2,400.00 to Elm City Properties from checking. Money moves now.") with **Yes, approve and pay** and **Cancel**. Reject asks the same way. After you confirm, a message at the bottom of the screen reports what happened, for example "Paid $2,400.00 to Elm City Properties. Ticket 102 is resolved."
- The section header shows a count that pulses pink when something is waiting. When nothing is waiting the section says so.
- Money only moves from the **Yes, approve and pay** click, which calls `POST /api/approvals/{id}/approve`.

## Reset

**Reset desk** opens an in-page dialog explaining that the working database goes back to the original (tickets reopen, cash goes back to where it started, pending payments are cleared), that the screen is cleared too, and that the audit trail is kept. Esc, a click outside, or Cancel closes it. **Yes, reset everything** calls `POST /api/reset`, clears the lanes and summary, and reloads tickets, approvals and cash. It's disabled while a run is going.

## Other states

- If the server isn't reachable, a red banner shows the command to start it, and the page retries every 3 seconds until it connects.
- Starting a run while another is going shows "The desk is already running a ticket…".
- Errors from the server show in the bottom message with the server's own text.
- Animations switch off for people who have reduced motion turned on.
- Buttons, board rows and the dialog can be used by keyboard (Esc closes the dialog), with visible focus rings.

## Creative choices and why they help

- **Tickets as flights on a departures board.** A board is built to be read at a glance from across a room: you see which tickets are still OPEN, which are waiting on you, and which are done without opening anything.
- **Split-flap status flips.** The flip is the one moving thing on the board when a status changes, so a ticket going to RESOLVED or AWAITING APPROVAL catches your eye even while you're looking at the lanes.
- **Agents as gates with their own color and icon.** Color is never the only cue (each lane also has a gate letter, icon and name), but it lets you follow a handoff across lanes by color alone, and the chips like Boss → Inventory make the route obvious.
- **Lanes dim until used.** Only the agents that were actually called light up, which makes it clear the boss is not sending everyone on every ticket.
- **Cash as a scoreboard with "after pending".** The person approving needs two numbers: what is in checking and what will be left. Both are always visible, and the drop animation ties the click to its effect on the balance, so a payment never goes through unnoticed.
- **Approvals pinned to the right.** The page's one human job, approving money, stays in view while you scroll through a long run.
- **Confirmation inside the card.** The question sits next to the amount and payee it's about, so you don't have to remember them, and nothing blocks the rest of the page like a browser popup would.
- **Summary cards in found / did / tools order.** They answer the three questions you'd ask about each agent in the order you'd ask them, using the agents' own reports.
- **Black and pink with hazard tape.** Dark, high-contrast screens are easy to read for long sessions, and the pink matches the project's black-and-pink theme.

## What isn't built

- The page follows a run by polling once a second. It does not use websockets.
- A run's id is held only in the page, so reloading the browser during a run loses the live view (the run itself continues on the server, and the board, cash and approvals still refresh).
- There is no history of past runs and no way to create tickets.
- Lane messages are short because the audit trail stores short text; the full agent reports are only in the run summary.

## Where the code is

`frontend/src/App.tsx` holds the state and polling. `components/` has the board, lanes, run summary, cash scoreboard, approvals, split-flap text, dialog and agent badges. `agents.tsx` defines the five agents' colors, icons and labels, `timeline.ts` turns the event list into lanes and handoffs, `api.ts` calls the backend, and `styles.css` has all the styling.
