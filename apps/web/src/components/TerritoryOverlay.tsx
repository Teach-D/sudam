'use client'

const CELL = 32
const MARGIN = 24
// 인접한 집들이 시각적으로 이어진 영역처럼 보이도록 셀 크기와 동일하게 설정
const HALF = 15   // 30×30 사각형 → 인접 셀과 2px 틈만 남음

interface TerritoryOverlayProps {
  black: [number, number][]
  white: [number, number][]
}

export function TerritoryOverlay({ black, white }: TerritoryOverlayProps) {
  return (
    <>
      {black.map(([row, col], i) => (
        <rect
          key={`b-${i}`}
          x={MARGIN + col * CELL - HALF}
          y={MARGIN + row * CELL - HALF}
          width={HALF * 2}
          height={HALF * 2}
          fill="#1a1a1a"
          opacity={0.55}
          rx={1}
        />
      ))}
      {white.map(([row, col], i) => (
        <rect
          key={`w-${i}`}
          x={MARGIN + col * CELL - HALF}
          y={MARGIN + row * CELL - HALF}
          width={HALF * 2}
          height={HALF * 2}
          fill="#ffffff"
          opacity={0.65}
          rx={1}
        />
      ))}
    </>
  )
}
