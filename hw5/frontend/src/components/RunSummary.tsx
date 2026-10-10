import { useState } from 'react'
import { agentInfo, agentKey } from '../agents'
import { STATUS_LABEL, formatMoney } from '../format'
import { AgentBadge, HandoffChip } from './AgentBadge'
import { FormattedText } from './FormattedText'
import type { AgentReport, RunEvent, RunResult, TicketStatus } from '../types'

interface Props {
  ticketId: number
  ticketStatus: TicketStatus | undefined
  result: RunResult | null
  error: string | null
  stoppedReason: string | null
  events: RunEvent[]
}

function Clamp({ children, long }: { children: React.ReactNode; long: boolean }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <div className={open || !long ? '' : 'clamp-box'}>{children}</div>
      {long && (
        <button className="link" onClick={() => setOpen(!open)}>
          {open ? 'Show less' : 'Show more'}
        </button>
      )}
    </>
  )
}

/** What an agent did, from its report plus the payments and status it set. */
function actionsFor(report: AgentReport, result: RunResult, events: RunEvent[], firstForAgent: boolean): string[] {
  const out: string[] = []
  const key = agentKey(report.agent)
  for (const to of report.delegated_to) out.push(`Handed work to ${agentInfo(to).name}`)
  if (report.tools_used.includes('prepare_payment') && firstForAgent) {
    for (const p of result.payment_requests.filter((x) => agentKey(x.prepared_by) === key)) {
      out.push(`Prepared a payment: ${formatMoney(p.amount)} to ${p.payee} (pending your approval, no money moved)`)
    }
  }
  if (report.tools_used.includes('record_customer_reply')) out.push('Saved a draft reply to the customer (nothing was sent)')
  if (report.tools_used.includes('update_ticket_status')) {
    const last = [...events].reverse().find((e) => agentKey(e.agent) === key && e.tool_or_target === 'update_ticket_status')
    const m = last && /"status":\s*"([a-z_]+)"/.exec(last.text)
    out.push(m ? `Set the ticket to ${(STATUS_LABEL[m[1]] ?? m[1]).toLowerCase()}` : 'Updated the ticket status')
  }
  return out
}

function countTools(tools: string[]): [string, number][] {
  const counts = new Map<string, number>()
  for (const t of tools) counts.set(t, (counts.get(t) ?? 0) + 1)
  return [...counts.entries()]
}

export function RunSummary({ ticketId, ticketStatus, result, error, stoppedReason, events }: Props) {
  const failed = error || stoppedReason
  const seenAgents = new Set<string>()

  return (
    <section className="panel summary" id="run-summary" aria-labelledby="summary-title">
      <header className="panel-head">
        <h2 id="summary-title">Run complete · Ticket {ticketId}</h2>
        {ticketStatus && <span className={`status-pill status-${ticketStatus}`}>{STATUS_LABEL[ticketStatus]}</span>}
      </header>

      {failed && (
        <div className="alert alert-error" role="alert">
          <strong>This run did not finish cleanly.</strong> {error ?? stoppedReason}
        </div>
      )}

      {result && (
        <>
          <div className="run-stats">
            <span className="route">
              {result.agents_involved.map((a, i) =>
                i === 0 ? (
                  <AgentBadge key={a} agent={a} />
                ) : (
                  <HandoffChip key={a} from={result.agents_involved[i - 1]} to={a} />
                ),
              )}
            </span>
            <span className="stat">
              <b>{result.requests}</b> model requests
            </span>
            <span className="stat">
              <b>{result.total_tokens.toLocaleString()}</b> tokens
            </span>
            <span className={`stat ${result.human_approval_needed ? 'stat-hot' : ''}`}>
              {result.human_approval_needed ? (
                <>
                  Needs your approval: <b>{formatMoney(result.approval_amount)}</b>
                </>
              ) : (
                'No approval needed'
              )}
            </span>
          </div>

          <div className="agent-cards">
            {result.reports
              .slice()
              .sort((a, b) => result.agents_involved.indexOf(a.agent) - result.agents_involved.indexOf(b.agent))
              .map((r, i) => {
                const a = agentInfo(r.agent)
                const first = !seenAgents.has(r.agent)
                seenAgents.add(r.agent)
                const did = actionsFor(r, result, events, first)
                return (
                  <article key={`${r.agent}-${i}`} className="agent-card" style={{ ['--c' as string]: a.color }}>
                    <header>
                      <span className="lane-icon">{a.icon}</span>
                      <div>
                        <strong>{a.name}</strong>
                        <span>{r.called_by ? `asked by ${agentInfo(r.called_by).name}` : a.role}</span>
                      </div>
                    </header>
                    <h3>What it found</h3>
                    <Clamp long={r.output.length > 420}>
                      <FormattedText text={r.output} />
                    </Clamp>
                    <h3>What it did</h3>
                    {did.length ? (
                      <ul className="did">
                        {did.map((d) => (
                          <li key={d}>{d}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">Looked things up and reported back. No changes made.</p>
                    )}
                    <h3>Tools used</h3>
                    <div className="tool-chips">
                      {r.tools_used.length === 0 && <span className="muted">none</span>}
                      {countTools(r.tools_used).map(([t, n]) => (
                        <span key={t} className="tool-chip">
                          {t}
                          {n > 1 ? ` ×${n}` : ''}
                        </span>
                      ))}
                    </div>
                  </article>
                )
              })}
          </div>
        </>
      )}
    </section>
  )
}
