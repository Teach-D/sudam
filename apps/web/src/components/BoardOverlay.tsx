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
}

export function BoardOverlay({ moves, visibleCount }: BoardOverlayProps) {
  const visible = visibleCount === 0 ? moves : moves.slice(0, visibleCount)

  return (
    <>
      {visible.map((mv, i) => {
        const x = MARGIN + mv.col * CELL
        const y = MARGIN + mv.row * CELL
        const isBlack = mv.color === 'B'
        return (
          <g key={i}>
            <circle
              cx={x}
              cy={y}
              r={13}
              fill={isBlack ? '#1a1a1a' : '#f5f5f5'}
              stroke={isBlack ? '#333' : '#999'}
              strokeWidth={1.5}
              opacity={0.85}
            />
            <text
              x={x}
              y={y + 5}
              textAnchor="middle"
              fontSize={12}
              fontWeight="bold"
              fill={isBlack ? '#f5c518' : '#c0392b'}
            >
              {mv.label}
            </text>
          </g>
        )
      })}
    </>
  )
}
