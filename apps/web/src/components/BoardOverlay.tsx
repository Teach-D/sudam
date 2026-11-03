'use client'

const CELL = 32
const MARGIN = 24

interface OverlayMove {
  row: number
  col: number
  color: string   // "B" | "W"
  label: string   // ① ② ③
}

interface BoardOverlayProps {
  moves: OverlayMove[]
  visibleCount: number   // 0 = 전체, n = n개까지만 표시
  hidden?: boolean       // true면 오버레이 숨김 (보드는 유지)
  badMoves?: { row: number; col: number }[]  // 나쁜 수 X 마커
}

export function BoardOverlay({ moves, visibleCount, hidden, badMoves }: BoardOverlayProps) {
  if (hidden && (!badMoves || badMoves.length === 0)) return null

  const visible = visibleCount === 0 ? moves : moves.slice(0, visibleCount)

  return (
    <>
      {!hidden && visible.map((mv, i) => {
        const x = MARGIN + mv.col * CELL
        const y = MARGIN + mv.row * CELL
        const isBlack = mv.color === 'B'
        return (
          <g key={i} pointerEvents="none">
            <circle
              cx={x}
              cy={y}
              r={13}
              fill={isBlack ? '#1a1a1a' : '#f5f5f5'}
              stroke={isBlack ? '#333' : '#999'}
              strokeWidth={1.5}
              opacity={0.6}
            />
            <text
              x={x}
              y={y + 5}
              textAnchor="middle"
              fontSize={12}
              fontWeight="bold"
              fill={isBlack ? '#f5c518' : '#c0392b'}
              opacity={0.9}
            >
              {mv.label}
            </text>
          </g>
        )
      })}

      {badMoves?.map((bm, i) => {
        const x = MARGIN + bm.col * CELL
        const y = MARGIN + bm.row * CELL
        const d = 7
        return (
          <g key={`bad-${i}`} pointerEvents="none">
            <circle cx={x} cy={y} r={13} fill="rgba(139,0,0,0.18)" stroke="#c0392b" strokeWidth={1.5} />
            <line x1={x - d} y1={y - d} x2={x + d} y2={y + d} stroke="#c0392b" strokeWidth={2.5} strokeLinecap="round" />
            <line x1={x + d} y1={y - d} x2={x - d} y2={y + d} stroke="#c0392b" strokeWidth={2.5} strokeLinecap="round" />
          </g>
        )
      })}
    </>
  )
}
