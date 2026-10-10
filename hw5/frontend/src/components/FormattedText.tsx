import type { ReactNode } from 'react'

function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0
  let m: RegExpExecArray | null
  let i = 0
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    const tok = m[0]
    parts.push(
      tok.startsWith('**') ? <strong key={i++}>{tok.slice(2, -2)}</strong> : <code key={i++}>{tok.slice(1, -1)}</code>,
    )
    last = m.index + tok.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

/** Tiny markdown: paragraphs, "- " bullets, **bold** and `code`. Enough for the agents' reports. */
export function FormattedText({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flush = (key: number) => {
    if (bullets.length) {
      blocks.push(
        <ul key={`ul-${key}`}>
          {bullets.map((b, i) => (
            <li key={i}>{inline(b)}</li>
          ))}
        </ul>,
      )
      bullets = []
    }
  }
  text.split('\n').forEach((raw, i) => {
    const line = raw.trim()
    if (/^[-•*] /.test(line)) {
      bullets.push(line.slice(2))
      return
    }
    flush(i)
    if (line) blocks.push(<p key={i}>{inline(line)}</p>)
  })
  flush(9999)
  return <div className="rich">{blocks}</div>
}
