import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, approvePayment, getApprovals, getCash, getEvents, getTickets, rejectPayment, resetDesk, startRun } from './api'
import { Approvals } from './components/Approvals'
import { CashBoard } from './components/CashBoard'
import { ConfirmDialog } from './components/ConfirmDialog'
import { Lanes } from './components/Lanes'
import { RunSummary } from './components/RunSummary'
import { TicketBoard } from './components/TicketBoard'
import { formatMoney } from './format'
import { buildTimeline } from './timeline'
import type { Cash, Payment, RunEvent, RunResult, Ticket } from './types'

type Phase = 'idle' | 'running' | 'done'
interface Notice {
  tone: 'ok' | 'error' | 'info'
  text: string
}

const errText = (e: unknown) => (e instanceof Error ? e.message : String(e))

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [approvals, setApprovals] = useState<Payment[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [offline, setOffline] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)

  const [phase, setPhase] = useState<Phase>('idle')
  const [starting, setStarting] = useState(false)
  const [runId, setRunId] = useState<string | null>(null)
  const [runTicketId, setRunTicketId] = useState<number | null>(null)
  const [events, setEvents] = useState<RunEvent[]>([])
  const [result, setResult] = useState<RunResult | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [stopped, setStopped] = useState<string | null>(null)
  const afterRef = useRef(0)

  const [busyPayment, setBusyPayment] = useState<number | null>(null)
  const [resetOpen, setResetOpen] = useState(false)
  const [resetBusy, setResetBusy] = useState(false)

  const refreshAll = useCallback(async () => {
    try {
      const [t, a, c] = await Promise.all([getTickets(), getApprovals(), getCash()])
      setTickets(t)
      setApprovals(a)
      setCash(c)
      setOffline(false)
      setSelectedId((cur) => cur ?? t[0]?.id ?? null)
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) setOffline(true)
      else setNotice({ tone: 'error', text: errText(e) })
    }
  }, [])

  useEffect(() => {
    void refreshAll()
  }, [refreshAll])

  // While the server is unreachable, keep trying so the board comes alive once it starts.
  useEffect(() => {
    if (!offline) return
    const id = window.setInterval(() => void refreshAll(), 3000)
    return () => window.clearInterval(id)
  }, [offline, refreshAll])

  useEffect(() => {
    if (!notice || notice.tone === 'error') return
    const id = window.setTimeout(() => setNotice(null), 7000)
    return () => window.clearTimeout(id)
  }, [notice])

  // Poll the run's events once a second while it is going.
  useEffect(() => {
    if (phase !== 'running' || !runId) return
    let cancelled = false
    let inflight = false
    let failures = 0

    const merge = (incoming: RunEvent[]) =>
      setEvents((prev) => {
        const seen = new Set(prev.map((e) => e.index))
        const fresh = incoming.filter((e) => !seen.has(e.index))
        return fresh.length ? [...prev, ...fresh] : prev
      })

    const tick = async () => {
      if (inflight) return
      inflight = true
      try {
        const res = await getEvents(runId, afterRef.current)
        if (cancelled) return
        failures = 0
        afterRef.current = res.next_after
        merge(res.events)
        if (res.finished) {
          // one more read so no late event is missed, then wrap up
          const last = await getEvents(runId, afterRef.current)
          if (cancelled) return
          afterRef.current = last.next_after
          merge(last.events)
          setResult(last.result ?? res.result)
          setRunError(last.error ?? res.error)
          setStopped(last.stopped_reason ?? res.stopped_reason)
          setPhase('done')
          void refreshAll()
        }
      } catch (e) {
        failures += 1
        if (failures === 3 && !cancelled) setNotice({ tone: 'error', text: `Lost the connection while following the run (${errText(e)}). Still retrying.` })
      } finally {
        inflight = false
      }
    }

    void tick()
    const id = window.setInterval(() => void tick(), 1000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [phase, runId, refreshAll])

  useEffect(() => {
    if (phase === 'done') document.getElementById('run-summary')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [phase])

  const timeline = useMemo(() => buildTimeline(events), [events])
  const running = phase === 'running'
  const selected = tickets.find((t) => t.id === selectedId) ?? null
  const runTicket = tickets.find((t) => t.id === runTicketId)

  async function onRun() {
    if (!selected || running || starting) return
    setStarting(true)
    try {
      const r = await startRun(selected.id)
      afterRef.current = 0
      setEvents([])
      setResult(null)
      setRunError(null)
      setStopped(null)
      setRunTicketId(r.ticket_id)
      setRunId(r.run_id)
      setPhase('running')
      setNotice(null)
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setNotice({ tone: 'error', text: 'The desk is already running a ticket. Wait for it to finish, then try again.' })
      } else {
        setNotice({ tone: 'error', text: errText(e) })
      }
    } finally {
      setStarting(false)
    }
  }

  async function onApprove(p: Payment) {
    setBusyPayment(p.id)
    try {
      const r = await approvePayment(p.id)
      setNotice({
        tone: 'ok',
        text: `Paid ${formatMoney(r.amount)} to ${r.payee}.${r.ticket_status ? ` Ticket ${r.ticket_id} is ${r.ticket_status}.` : ''}`,
      })
      await refreshAll()
    } catch (e) {
      setNotice({ tone: 'error', text: errText(e) })
      await refreshAll()
    } finally {
      setBusyPayment(null)
    }
  }

  async function onReject(p: Payment) {
    setBusyPayment(p.id)
    try {
      await rejectPayment(p.id)
      setNotice({ tone: 'info', text: `Rejected the ${formatMoney(p.amount)} payment to ${p.payee}. Cash was not touched.` })
      await refreshAll()
    } catch (e) {
      setNotice({ tone: 'error', text: errText(e) })
      await refreshAll()
    } finally {
      setBusyPayment(null)
    }
  }

  async function onReset() {
    setResetBusy(true)
    try {
      await resetDesk()
      setPhase('idle')
      setRunId(null)
      setRunTicketId(null)
      setEvents([])
      setResult(null)
      setRunError(null)
      setStopped(null)
      afterRef.current = 0
      setResetOpen(false)
      setNotice({ tone: 'ok', text: 'Desk reset. Tickets, cash and payments are back to the starting data.' })
      await refreshAll()
    } catch (e) {
      setResetOpen(false)
      setNotice({ tone: 'error', text: errText(e) })
    } finally {
      setResetBusy(false)
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            CC
          </span>
          <div>
            <h1>
              Campus Customs <span>Ops Desk</span>
            </h1>
            <p>Yale merch shop · Chapel Street</p>
          </div>
        </div>
        <button className="btn btn-ghost" onClick={() => setResetOpen(true)} disabled={running || offline} title={running ? 'Wait for the run to finish' : undefined}>
          Reset desk
        </button>
      </header>

      {offline && (
        <div className="alert alert-error" role="alert">
          <strong>Can't reach the desk server.</strong> Start it, and this page will connect on its own:
          <code>cd backend &amp;&amp; ../.venv/bin/uvicorn main:app --reload --port 8000</code>
        </div>
      )}

      <main className="grid">
        <div className="area-board">
          <TicketBoard tickets={tickets} selectedId={selectedId} workingId={running ? runTicketId : null} deskDate={cash?.as_of ?? null} onSelect={setSelectedId} />
        </div>

        <div className="area-runbar runbar">
          <div className="runbar-info">
            {selected ? (
              <>
                <span className="runbar-label">Selected</span>
                <strong>
                  CC{selected.id} · {selected.subject}
                </strong>
              </>
            ) : (
              <span className="muted">No ticket selected</span>
            )}
          </div>
          <div className="runbar-state" aria-live="polite">
            {running && (
              <span className="live">
                <i /> Run in progress · following every second
              </span>
            )}
            {phase === 'done' && (
              <span className="muted">
                Run finished · ticket {runTicketId} is {runTicket?.status.replace('_', ' ')}
              </span>
            )}
          </div>
          <button className="btn btn-run" onClick={() => void onRun()} disabled={!selected || running || starting || offline}>
            {running ? 'Run in progress…' : starting ? 'Starting…' : `▶ Run ticket ${selected?.id ?? ''}`}
          </button>
        </div>

        <aside className="area-side">
          <CashBoard cash={cash} />
          <Approvals payments={approvals} busyId={busyPayment} onApprove={(p) => void onApprove(p)} onReject={(p) => void onReject(p)} />
        </aside>

        <div className="area-lanes">
          <Lanes timeline={timeline} running={running} hasRun={runId !== null} />
        </div>

        {phase === 'done' && runTicketId !== null && (
          <div className="area-summary">
            <RunSummary ticketId={runTicketId} ticketStatus={runTicket?.status} result={result} error={runError} stoppedReason={stopped} events={events} />
          </div>
        )}
      </main>

      {notice && (
        <div className={`ticker ticker-${notice.tone}`} role={notice.tone === 'error' ? 'alert' : 'status'}>
          <span>{notice.text}</span>
          <button className="link" onClick={() => setNotice(null)} aria-label="Dismiss">
            ✕
          </button>
        </div>
      )}

      {resetOpen && (
        <ConfirmDialog title="Reset the desk?" confirmLabel="Yes, reset everything" busy={resetBusy} onConfirm={() => void onReset()} onCancel={() => setResetOpen(false)}>
          <p>
            This puts the working database back to the original: tickets reopen, cash goes back to where it started, and pending payments are cleared. This screen is cleared too.
          </p>
          <p className="muted">The audit trail is kept.</p>
        </ConfirmDialog>
      )}
    </div>
  )
}
