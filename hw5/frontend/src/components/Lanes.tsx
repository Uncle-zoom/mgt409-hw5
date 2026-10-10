import { useEffect, useRef, useState } from 'react'
import { AGENTS, agentInfo, type AgentInfo, type AgentKey } from '../agents'
import { HandoffChip } from './AgentBadge'
import { FormattedText } from './FormattedText'
import type { LaneItem, Timeline } from '../timeline'

function ClampText({ text, className }: { text: string; className?: string }) {
  const [open, setOpen] = useState(false)
  if (!text) return null
  const long = text.length > 110
  return (
    <span className={className}>
      <span className={open || !long ? '' : 'clamp'}>{text}</span>
      {long && (
        <button className="link" onClick={() => setOpen(!open)}>
          {open ? 'less' : 'more'}
        </button>
      )}
    </span>
  )
}

function Item({ item }: { item: LaneItem }) {
  const num = <span className="seq">#{String(item.index).padStart(2, '0')}</span>
  switch (item.kind) {
    case 'message':
      return (
        <li className="item item-message">
          {num}
          <div className="bubble">
            <FormattedText text={item.text} />
          </div>
        </li>
      )
    case 'plan':
      return (
        <li className="item item-plan">
          {num}
          <span>
            decides to {item.tools.map((t) => (t === 'delegate' ? 'hand off' : `call ${t}`)).join(', ') || 'act'}
          </span>
        </li>
      )
    case 'tool':
      return (
        <li className="item item-tool">
          {num}
          <div>
            <div className="tool-line">
              <span className="tool-chip">{item.tool}</span>
              {item.args && item.args !== '{}' && <ClampText className="tool-args" text={item.args} />}
            </div>
            {item.result && <ClampText className="tool-result" text={item.result} />}
          </div>
        </li>
      )
    case 'handoff-out':
      return (
        <li className="item item-handoff">
          {num}
          <HandoffChip from={item.from} to={item.to} />
          <span className="muted">handed off</span>
        </li>
      )
    case 'handoff-in':
      return (
        <li className="item item-handoff">
          {num}
          <HandoffChip from={item.from} to={item.to} />
          <span className="muted">picked up the task</span>
        </li>
      )
    case 'report-back':
      return (
        <li className="item item-handoff">
          {num}
          <span className="muted">report back from</span>
          <span className="inline-agent" style={{ color: agentInfo(item.from).color }}>
            {agentInfo(item.from).name}
          </span>
        </li>
      )
    case 'blocked':
      return (
        <li className="item item-blocked">
          {num}
          <span>
            Handoff to <b>{item.to}</b> blocked: {item.reason}
          </span>
        </li>
      )
  }
}

function Lane({ agent, items, active, running }: { agent: AgentInfo; items: LaneItem[]; active: boolean; running: boolean }) {
  const body = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = body.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [items.length])

  const state = active ? 'active' : items.length ? 'done' : 'idle'
  const label = active ? 'WORKING' : items.length ? (running ? 'WAITING' : 'DONE') : 'STANDING BY'

  return (
    <li className={`lane lane-${state}`} style={{ ['--c' as string]: agent.color }} aria-label={`${agent.name} lane`}>
      <div className="lane-head">
        <span className="gate">GATE {agent.gate}</span>
        <span className="lane-icon">{agent.icon}</span>
        <div className="lane-title">
          <strong>{agent.name}</strong>
          <span>{agent.role}</span>
        </div>
        <span className="lane-state">
          <i /> {label}
        </span>
      </div>
      {items.length > 0 && (
        <div className="lane-body" ref={body}>
          <ol>
            {items.map((it) => (
              <Item key={`${it.index}-${it.kind}`} item={it} />
            ))}
          </ol>
        </div>
      )}
    </li>
  )
}

interface Props {
  timeline: Timeline
  running: boolean
  hasRun: boolean
}

export function Lanes({ timeline, running, hasRun }: Props) {
  return (
    <section className="panel gates" aria-labelledby="gates-title">
      <header className="panel-head">
        <h2 id="gates-title">Gates</h2>
        {timeline.handoffs.length > 0 && (
          <span className="route" aria-label="Route of this run">
            {timeline.handoffs.map((h) => (
              <HandoffChip key={h.index} from={h.from} to={h.to} />
            ))}
          </span>
        )}
      </header>
      {!hasRun && <p className="muted empty-note">Pick a ticket and press Run. Each agent lights up at its own gate as it works.</p>}
      <ul className="lanes">
        {AGENTS.map((a) => (
          <Lane key={a.key} agent={a} items={timeline.lanes[a.key as AgentKey]} active={running && timeline.current === a.key} running={running} />
        ))}
      </ul>
    </section>
  )
}
