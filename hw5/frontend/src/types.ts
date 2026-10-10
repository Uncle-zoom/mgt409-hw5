export type TicketStatus = 'open' | 'awaiting_approval' | 'resolved'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  status: TicketStatus
}

export interface Payment {
  id: number
  ticket_id: number
  kind: string
  ref_id: number
  payee: string
  amount: number
  reason: string | null
  prepared_by: string
  status: string
  created_on: string
}

export interface Cash {
  account: string
  balance: number
  as_of: string
  pending_payments_total: number
  balance_after_pending: number
}

export type StepType = 'model_call' | 'tool_call' | 'delegation'

export interface RunEvent {
  index: number
  timestamp: string
  agent: string
  step_type: StepType
  tool_or_target: string | null
  text: string
  tokens: { input: number; output: number; total: number } | null
  stop_reason: string | null
}

export interface AgentReport {
  agent: string
  called_by: string | null
  task: string
  output: string
  depth: number
  requests: number
  input_tokens: number
  output_tokens: number
  tools_used: string[]
  delegated_to: string[]
}

export interface RunResult {
  run_id: string
  ticket_id: number
  outcome: string
  stopped_reason: string | null
  agents_involved: string[]
  tools_used: string[]
  payment_requests: Payment[]
  human_approval_needed: boolean
  approval_amount: number
  requests: number
  total_tokens: number
  reports: AgentReport[]
}

export interface EventsResponse {
  run_id: string
  ticket_id: number
  events: RunEvent[]
  next_after: number
  finished: boolean
  summary: string | null
  stopped_reason: string | null
  error: string | null
  result: RunResult | null
}

export interface ApproveResponse {
  approved: true
  payment_id: number
  ticket_id: number
  amount: number
  payee: string
  new_checking_balance: number
  invoice_status: string | null
  ticket_status: string | null
}
