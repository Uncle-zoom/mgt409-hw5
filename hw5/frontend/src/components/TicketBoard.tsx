import type { Ticket } from '../types'
import { FlapText, type FlapTone } from './FlapText'
import { STATUS_LABEL, TYPE_LABEL } from '../format'

const STATUS_TONE: Record<string, FlapTone> = { open: 'plain', awaiting_approval: 'yellow', resolved: 'green' }

interface Props {
  tickets: Ticket[]
  selectedId: number | null
  workingId: number | null
  deskDate: string | null
  onSelect: (id: number) => void
}

export function TicketBoard({ tickets, selectedId, workingId, deskDate, onSelect }: Props) {
  return (
    <section className="panel board" aria-labelledby="board-title">
      <header className="board-head">
        <h2 id="board-title">
          <span className="plane" aria-hidden="true">
            ✈
          </span>{' '}
          Departures
        </h2>
        <span className="board-date">{deskDate ? `DESK DATE ${deskDate}` : 'DESK DATE —'}</span>
      </header>

      <div className="board-cols" aria-hidden="true">
        <span>Flight</span>
        <span>Type</span>
        <span>From</span>
        <span>Subject</span>
        <span>Status</span>
      </div>

      <ul className="board-rows" role="listbox" aria-label="Tickets">
        {tickets.length === 0 && <li className="board-empty">No tickets on the board.</li>}
        {tickets.map((t) => {
          const selected = t.id === selectedId
          return (
            <li key={t.id} role="option" aria-selected={selected}>
              <button className={`board-row${selected ? ' selected' : ''}`} onClick={() => onSelect(t.id)}>
                <span className="cell cell-flight">
                  <span className="pointer" aria-hidden="true">
                    {selected ? '▶' : ''}
                  </span>
                  <FlapText text={`CC${t.id}`} size="md" />
                </span>
                <span className="cell cell-type">{TYPE_LABEL[t.type] ?? t.type.toUpperCase()}</span>
                <span className="cell cell-from">{t.requester}</span>
                <span className="cell cell-subject">{t.subject}</span>
                <span className="cell cell-status">
                  <FlapText text={STATUS_LABEL[t.status] ?? t.status.toUpperCase()} tone={STATUS_TONE[t.status] ?? 'plain'} size="sm" />
                  {workingId === t.id && (
                    <span className="working" title="Agents are working this ticket">
                      <i /> working
                    </span>
                  )}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
