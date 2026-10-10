import type { ReactNode } from 'react'

export type AgentKey = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface AgentInfo {
  key: AgentKey
  name: string
  role: string
  gate: string
  color: string
  icon: ReactNode
}

const svg = (children: ReactNode) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {children}
  </svg>
)

export const AGENTS: AgentInfo[] = [
  {
    key: 'boss',
    name: 'Boss',
    role: 'Desk manager',
    gate: 'A',
    color: '#ff3d97',
    // clipboard with a check
    icon: svg(
      <>
        <rect x="5" y="4" width="14" height="17" rx="2" />
        <path d="M9 4h6v3H9z" />
        <path d="m9 14 2.2 2.2L15.5 12" />
      </>,
    ),
  },
  {
    key: 'inventory',
    name: 'Inventory',
    role: 'Stock and restock',
    gate: 'B',
    color: '#4cc9ff',
    // stacked boxes
    icon: svg(
      <>
        <path d="M12 3 4 7l8 4 8-4-8-4Z" />
        <path d="M4 7v10l8 4 8-4V7" />
        <path d="M12 11v10" />
      </>,
    ),
  },
  {
    key: 'accounting',
    name: 'Accounting',
    role: 'Invoices, cash and pricing',
    gate: 'C',
    color: '#ff9f43',
    // coin
    icon: svg(
      <>
        <circle cx="12" cy="12" r="8.5" />
        <path d="M14.8 9.2c-.5-.9-1.6-1.4-2.8-1.4-1.5 0-2.6.8-2.6 2 0 3 5.4 1.3 5.4 4.2 0 1.2-1.2 2-2.8 2-1.3 0-2.4-.6-3-1.6" />
        <path d="M12 6.2v1.6M12 16.2v1.6" />
      </>,
    ),
  },
  {
    key: 'facilities',
    name: 'Facilities',
    role: 'Lease and rent',
    gate: 'D',
    color: '#b6f23a',
    // building
    icon: svg(
      <>
        <path d="M4 21V8l8-5 8 5v13" />
        <path d="M3 21h18" />
        <path d="M9 21v-6h6v6" />
        <path d="M9 11h.01M15 11h.01" />
      </>,
    ),
  },
  {
    key: 'customer_service',
    name: 'Customer Service',
    role: 'Customer replies',
    gate: 'E',
    color: '#b794ff',
    // chat bubble
    icon: svg(
      <>
        <path d="M20 12a8 8 0 0 1-11.6 7.1L4 20l1-4.1A8 8 0 1 1 20 12Z" />
        <path d="M9 11h6M9 14h3.5" />
      </>,
    ),
  },
]

const byKey = new Map(AGENTS.map((a) => [a.key, a]))

export function agentKey(raw: string): AgentKey {
  const k = raw.trim().toLowerCase().replace(/[\s-]+/g, '_')
  return (byKey.has(k as AgentKey) ? k : 'boss') as AgentKey
}

export const agentInfo = (raw: string): AgentInfo => byKey.get(agentKey(raw))!
