import { useEffect, useRef, useState } from 'react'
import { formatMoney } from '../format'
import type { Cash } from '../types'

/** Eases a number toward its new target. The first real value just appears. */
function useTween(target: number | null, ms = 1300): number {
  const [value, setValue] = useState(target ?? 0)
  const from = useRef(target ?? 0)
  const seen = useRef(target !== null)

  useEffect(() => {
    if (target === null) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!seen.current || reduce) {
      seen.current = true
      from.current = target
      setValue(target)
      return
    }
    const start = performance.now()
    const a = from.current
    if (a === target) return
    let raf = 0
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / ms)
      const eased = 1 - Math.pow(1 - p, 3)
      const cur = a + (target - a) * eased
      from.current = cur
      setValue(cur)
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])

  return value
}

function Digits({ value, className, dim }: { value: number; className?: string; dim?: boolean }) {
  const text = dim ? '$-,---.--' : formatMoney(Math.max(0, Math.round(value * 100) / 100))
  return (
    <span className={`digits ${className ?? ''}${dim ? ' digits-dim' : ''}`} aria-hidden="true">
      {[...text].map((ch, i) => (
        <span key={i} className={/\d/.test(ch) ? 'digit' : 'digit digit-sep'}>
          {ch}
        </span>
      ))}
    </span>
  )
}

export function CashBoard({ cash }: { cash: Cash | null }) {
  const balance = useTween(cash ? cash.balance : null)
  const after = useTween(cash ? cash.balance_after_pending : null)
  const pending = useTween(cash ? cash.pending_payments_total : null)

  const prev = useRef<number | null>(null)
  const [drop, setDrop] = useState<number | null>(null)
  useEffect(() => {
    if (!cash) return
    if (prev.current !== null && cash.balance < prev.current) {
      const amount = prev.current - cash.balance
      setDrop(amount)
      const t = window.setTimeout(() => setDrop(null), 4500)
      prev.current = cash.balance
      return () => window.clearTimeout(t)
    }
    prev.current = cash.balance
  }, [cash])

  return (
    <section className="panel scoreboard" aria-labelledby="cash-title">
      <header className="score-head">
        <h2 id="cash-title">Checking</h2>
        <span className="score-asof">{cash ? `AS OF ${cash.as_of}` : '—'}</span>
      </header>

      <div className={`score-main${drop !== null ? ' dropping' : ''}`} role="status" aria-live="polite">
        <span className="sr-only">{cash ? `Checking balance ${formatMoney(cash.balance)}` : 'Checking balance loading'}</span>
        <Digits value={balance} dim={!cash} />
        {drop !== null && <span className="drop-chip">−{formatMoney(drop)}</span>}
      </div>

      <dl className="score-sub">
        <div>
          <dt>Pending approval</dt>
          <dd>
            <Digits value={pending} dim={!cash} className="digits-sm" />
          </dd>
        </div>
        <div>
          <dt>After pending</dt>
          <dd>
            <Digits value={after} dim={!cash} className="digits-sm digits-hot" />
          </dd>
        </div>
      </dl>
    </section>
  )
}
