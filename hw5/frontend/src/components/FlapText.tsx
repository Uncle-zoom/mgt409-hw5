export type FlapTone = 'plain' | 'yellow' | 'green' | 'pink'
export type FlapSize = 'sm' | 'md' | 'lg' | 'xl'

interface Props {
  text: string
  tone?: FlapTone
  size?: FlapSize
}

/**
 * Split-flap text. Every character is its own tile; a tile re-mounts (and flips) only when
 * its character changes, so OPEN -> RESOLVED flips the way a departures board does.
 */
export function FlapText({ text, tone = 'plain', size = 'md' }: Props) {
  return (
    <span className={`flap flap-${size} tone-${tone}`}>
      <span className="sr-only">{text}</span>
      {[...text].map((ch, i) =>
        ch === ' ' ? (
          <span key={`${i}-gap`} className="flap-gap" aria-hidden="true" />
        ) : (
          <span key={`${i}-${ch}`} className="flap-ch" style={{ animationDelay: `${Math.min(i, 24) * 32}ms` }} aria-hidden="true">
            {ch}
          </span>
        ),
      )}
    </span>
  )
}
