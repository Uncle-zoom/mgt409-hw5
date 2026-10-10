import type { ApproveResponse, Cash, EventsResponse, Payment, Ticket } from './types'

export const API_BASE = 'http://localhost:8000'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new ApiError(0, `Can't reach the desk server at ${API_BASE}.`)
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* keep the status text */
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })

export const getTickets = () => request<{ tickets: Ticket[] }>('/api/tickets').then((r) => r.tickets)
export const getApprovals = () =>
  request<{ payments: Payment[]; pending_total: number }>('/api/approvals').then((r) => r.payments)
export const getCash = () => request<Cash>('/api/cash')
export const startRun = (ticketId: number) =>
  post<{ run_id: string; ticket_id: number }>(`/api/tickets/${ticketId}/run`)
export const getEvents = (runId: string, after: number) =>
  request<EventsResponse>(`/api/events?run_id=${encodeURIComponent(runId)}&after=${after}`)
export const approvePayment = (id: number) =>
  post<ApproveResponse>(`/api/approvals/${id}/approve`)
export const rejectPayment = (id: number) => post<{ rejected: true; payment_id: number }>(`/api/approvals/${id}/reject`)
export const resetDesk = () => post<{ reset: true }>('/api/reset')
