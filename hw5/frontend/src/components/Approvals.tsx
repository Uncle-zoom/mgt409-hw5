import { useState } from 'react'
import { AgentBadge } from './AgentBadge'
import { formatMoney } from '../format'
import type { Payment } from '../types'

interface Props {
  payments: Payment[]
  busyId: number | null
  onApprove: (p: Payment) => void
  onReject: (p: Payment) => void
}

type Pending = { id: number; action: 'approve' | 'reject' } | null

export function Approvals({ payments, busyId, onApprove, onReject }: Props) {
  const [confirming, setConfirming] = useState<Pending>(null)

  return (
    <section className="panel approvals" aria-labelledby="approvals-title">
      <header className="panel-head">
        <h2 id="approvals-title">Waiting for your OK</h2>
        <span className={`count${payments.length ? ' count-hot' : ''}`}>{payments.length}</span>
      </header>

      {payments.length === 0 && (
        <p className="muted empty-note">Nothing waiting. Payments Accounting prepares land here for a human to approve.</p>
      )}

      <ul className="cards">
        {payments.map((p) => {
          const asking = confirming?.id === p.id ? confirming.action : null
          const busy = busyId === p.id
          return (
            <li key={p.id} className="pay-card">
              <div className="pay-top">
                <span className="pay-amount">{formatMoney(p.amount)}</span>
                <span className="pay-ticket">Ticket {p.ticket_id}</span>
              </div>
              <div className="pay-payee">{p.payee}</div>
              <dl className="pay-meta">
                <div>
                  <dt>For</dt>
                  <dd>
                    {p.kind} #{p.ref_id}
                  </dd>
                </div>
                <div>
                  <dt>Prepared by</dt>
                  <dd>
                    <AgentBadge agent={p.prepared_by} />
                  </dd>
                </div>
              </dl>
              {p.reason && <p className="pay-reason">{p.reason}</p>}

              {asking === null ? (
                <div className="pay-actions">
                  <button className="btn btn-primary" disabled={busy} onClick={() => setConfirming({ id: p.id, action: 'approve' })}>
                    Approve
                  </button>
                  <button className="btn btn-ghost" disabled={busy} onClick={() => setConfirming({ id: p.id, action: 'reject' })}>
                    Reject
                  </button>
                </div>
              ) : (
                <div className={`pay-confirm ${asking}`} role="alertdialog" aria-label="Confirm">
                  <p>
                    <strong>Are you sure?</strong>{' '}
                    {asking === 'approve'
                      ? `This pays ${formatMoney(p.amount)} to ${p.payee} from checking. Money moves now.`
                      : `This rejects the ${formatMoney(p.amount)} payment to ${p.payee}. Cash is not touched.`}
                  </p>
                  <div className="pay-actions">
                    <button
                      className={asking === 'approve' ? 'btn btn-primary' : 'btn btn-danger'}
                      disabled={busy}
                      onClick={() => {
                        setConfirming(null)
                        if (asking === 'approve') onApprove(p)
                        else onReject(p)
                      }}
                    >
                      {asking === 'approve' ? 'Yes, approve and pay' : 'Yes, reject'}
                    </button>
                    <button className="btn btn-ghost" onClick={() => setConfirming(null)}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
