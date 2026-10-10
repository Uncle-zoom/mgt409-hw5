import { agentInfo } from '../agents'

export function AgentBadge({ agent, compact }: { agent: string; compact?: boolean }) {
  const a = agentInfo(agent)
  return (
    <span className="agent-badge" style={{ ['--c' as string]: a.color }}>
      <span className="agent-badge-icon">{a.icon}</span>
      {!compact && a.name}
    </span>
  )
}

export function HandoffChip({ from, to }: { from: string; to: string }) {
  const f = agentInfo(from)
  const t = agentInfo(to)
  return (
    <span className="handoff-chip">
      <span style={{ color: f.color }}>{f.name}</span>
      <span className="handoff-arrow" aria-hidden="true">
        →
      </span>
      <span style={{ color: t.color }}>{t.name}</span>
    </span>
  )
}
