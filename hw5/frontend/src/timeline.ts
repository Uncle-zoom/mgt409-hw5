import { agentKey, type AgentKey } from './agents'
import type { RunEvent } from './types'

export type LaneItem =
  | { kind: 'message'; index: number; text: string }
  | { kind: 'plan'; index: number; tools: string[] }
  | { kind: 'tool'; index: number; tool: string; args: string; result: string }
  | { kind: 'handoff-out'; index: number; from: AgentKey; to: AgentKey }
  | { kind: 'handoff-in'; index: number; from: AgentKey; to: AgentKey }
  | { kind: 'report-back'; index: number; from: AgentKey }
  | { kind: 'blocked'; index: number; to: string; reason: string }

export interface Timeline {
  lanes: Record<AgentKey, LaneItem[]>
  /** the agent working right now (top of the delegation stack at the last event) */
  current: AgentKey | null
  handoffs: { index: number; from: AgentKey; to: AgentKey }[]
}

const emptyLanes = (): Record<AgentKey, LaneItem[]> => ({
  boss: [],
  inventory: [],
  accounting: [],
  facilities: [],
  customer_service: [],
})

/** Split the audit entry's "args → result" text back into its two parts. */
export function splitToolText(text: string): { args: string; result: string } {
  const at = text.indexOf(' → ')
  if (at < 0) return { args: text, result: '' }
  return { args: text.slice(0, at), result: text.slice(at + 3) }
}

/**
 * Turn the flat, ordered event list into per-agent lanes. Handoffs are detected from the
 * order of events: a new agent speaking means the caller handed work to it, and the caller
 * speaking again (or logging its delegation) means the work came back.
 */
export function buildTimeline(events: RunEvent[]): Timeline {
  const lanes = emptyLanes()
  const handoffs: Timeline['handoffs'] = []
  const stack: AgentKey[] = []

  for (const ev of events) {
    const agent = agentKey(ev.agent)
    if (stack.length === 0) {
      stack.push(agent)
    } else if (stack[stack.length - 1] !== agent) {
      const back = stack.lastIndexOf(agent)
      if (back >= 0) {
        stack.length = back + 1 // the called agent finished, we are back with its caller
      } else {
        const from = stack[stack.length - 1]
        stack.push(agent)
        handoffs.push({ index: ev.index, from, to: agent })
        lanes[from].push({ kind: 'handoff-out', index: ev.index, from, to: agent })
        lanes[agent].push({ kind: 'handoff-in', index: ev.index, from, to: agent })
      }
    }

    if (ev.step_type === 'model_call') {
      const m = /^requested tools: \[(.*)\]$/.exec(ev.text)
      if (m) {
        const tools = [...m[1].matchAll(/'([^']+)'/g)].map((t) => t[1])
        lanes[agent].push({ kind: 'plan', index: ev.index, tools })
      } else if (ev.text) {
        lanes[agent].push({ kind: 'message', index: ev.index, text: ev.text })
      }
    } else if (ev.step_type === 'tool_call') {
      const { args, result } = splitToolText(ev.text)
      lanes[agent].push({ kind: 'tool', index: ev.index, tool: ev.tool_or_target ?? 'tool', args, result })
    } else {
      const to = ev.tool_or_target ?? ''
      const blocked = /BLOCKED: (.*)$/.exec(ev.text)
      if (blocked) {
        lanes[agent].push({ kind: 'blocked', index: ev.index, to, reason: blocked[1] })
      } else {
        lanes[agent].push({ kind: 'report-back', index: ev.index, from: agentKey(to) })
      }
    }
  }
  return { lanes, current: stack.length ? stack[stack.length - 1] : null, handoffs }
}
