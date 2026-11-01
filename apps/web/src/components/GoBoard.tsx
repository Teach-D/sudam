'use client'

import { useCallback, ReactNode } from 'react'
import type { CoordMarker } from '@/lib/coordHighlight'

const BOARD_SIZE = 19
const CELL = 32        // px per grid cell
const MARGIN = 24      // px around the grid
const STONE_R = 14     // stone radius
const SVG_SIZE = (BOARD_SIZE - 1) * CELL + MARGIN * 2

// Korean column labels (가 나 다 ...)
const KR_COLS = '가나다라마바사아자차카타파하거너더러머'

function toKorean(row: number, col: number): string {
  return KR_COLS[col] + String(BOARD_SIZE - row)
}

function starPoints(): [number, number][] {
  const pts: [number, number][] = []
  for (const r of [3, 9, 15]) {
    for (const c of [3, 9, 15]) {
      pts.push([r, c])
    }
  }
  return pts
}

interface GoBoardProps {
  board: number[][]
  moveHistory: Array<{ row: number; col: number; color: 1 | 2; moveNumber: number }>
  currentPlayer: 1 | 2
  onPlace: (row: number, col: number) => void
  disabled?: boolean
  bgOverlay?: ReactNode  // 돌 아래에 렌더링 (집 표시 등)
  overlay?: ReactNode    // 돌 위에 렌더링 (수순 오버레이 등)
  pinMode?: boolean                                  // true면 빈 셀 클릭 시 onPin 호출
  onPin?: (row: number, col: number) => void
  pinnedCell?: { row: number; col: number } | null
  coachCoordMarkers?: CoordMarker[]
}

export function GoBoard({ board, moveHistory, currentPlayer, onPlace, disabled, bgOverlay, overlay, pinMode, onPin, pinnedCell, coachCoordMarkers }: GoBoardProps) {
  const toXY = useCallback(
    (row: number, col: number) => ({
      x: MARGIN + col * CELL,
      y: MARGIN + row * CELL,
    }),
    [],
  )

  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const rect = e.currentTarget.getBoundingClientRect()
      const px = e.clientX - rect.left
      const py = e.clientY - rect.top
      const col = Math.round((px - MARGIN) / CELL)
      const row = Math.round((py - MARGIN) / CELL)
      if (row < 0 || row >= BOARD_SIZE || col < 0 || col >= BOARD_SIZE) return
      if (board[row][col] !== 0) return
      if (pinMode) {
        onPin?.(row, col)
      } else {
        if (disabled) return
        onPlace(row, col)
      }
    },
    [disabled, board, onPlace, onPin, pinMode],
  )

  const lastMove = moveHistory.at(-1)

  return (
    <svg
      width={SVG_SIZE}
      height={SVG_SIZE}
      onClick={handleClick}
      className={pinMode ? 'cursor-crosshair' : disabled ? 'cursor-not-allowed' : 'cursor-pointer'}
      style={{ background: '#dcb468', borderRadius: 4 }}
    >
      {/* Grid lines */}
      {Array.from({ length: BOARD_SIZE }, (_, i) => {
        const { x: x0 } = toXY(i, 0)
        const { x: x1 } = toXY(i, BOARD_SIZE - 1)
        const { y: y0 } = toXY(0, i)
        const { y: y1 } = toXY(BOARD_SIZE - 1, i)
        return (
          <g key={i}>
            <line x1={x0} y1={toXY(i, 0).y} x2={x1} y2={toXY(i, 0).y} stroke="#8b6914" strokeWidth={0.8} />
            <line x1={toXY(0, i).x} y1={y0} x2={toXY(0, i).x} y2={y1} stroke="#8b6914" strokeWidth={0.8} />
          </g>
        )
      })}

      {/* Star points */}
      {starPoints().map(([r, c]) => {
        const { x, y } = toXY(r, c)
        return <circle key={`${r}-${c}`} cx={x} cy={y} r={3} fill="#8b6914" />
      })}

      {/* Coordinate labels */}
      {Array.from({ length: BOARD_SIZE }, (_, i) => (
        <g key={`label-${i}`}>
          <text
            x={MARGIN + i * CELL}
            y={MARGIN - 8}
            textAnchor="middle"
            fontSize={10}
            fill="#5a3e1b"
          >
            {KR_COLS[i]}
          </text>
          <text
            x={MARGIN - 12}
            y={MARGIN + i * CELL + 4}
            textAnchor="middle"
            fontSize={10}
            fill="#5a3e1b"
          >
            {BOARD_SIZE - i}
          </text>
        </g>
      ))}

      {/* 집 표시 등 돌 아래 배경 오버레이 */}
      {bgOverlay}

      {/* Stones */}
      {board.flatMap((rowArr, r) =>
        rowArr.map((cell, c) => {
          if (cell === 0) return null
          const { x, y } = toXY(r, c)
          const isBlack = cell === 1
          const moveRecord = moveHistory.find((m) => m.row === r && m.col === c)
          const isLast = lastMove?.row === r && lastMove?.col === c

          return (
            <g key={`${r}-${c}`}>
              <circle
                cx={x}
                cy={y}
                r={STONE_R}
                fill={isBlack ? '#1a1a1a' : '#f5f5f5'}
                stroke={isBlack ? '#000' : '#999'}
                strokeWidth={1}
              />
              {/* Move number */}
              {moveRecord && (
                <text
                  x={x}
                  y={y + 4}
                  textAnchor="middle"
                  fontSize={9}
                  fontWeight="bold"
                  fill={isBlack ? '#fff' : '#333'}
                >
                  {moveRecord.moveNumber}
                </text>
              )}
              {/* Last move marker */}
              {isLast && (
                <circle
                  cx={x}
                  cy={y}
                  r={4}
                  fill="none"
                  stroke={isBlack ? '#e8c843' : '#c0392b'}
                  strokeWidth={2}
                />
              )}
            </g>
          )
        }),
      )}

      {/* 좌표 핀 마커 */}
      {pinnedCell && board[pinnedCell.row]?.[pinnedCell.col] === 0 && (() => {
        const { x, y } = toXY(pinnedCell.row, pinnedCell.col)
        return (
          <circle
            cx={x}
            cy={y}
            r={STONE_R}
            fill="rgba(59,130,246,0.18)"
            stroke="#3b82f6"
            strokeWidth={2.5}
            strokeDasharray="5 2"
            pointerEvents="none"
          />
        )
      })()}

      {/* 수순 오버레이 */}
      {overlay}

      {/* 코치 답변 좌표 마커 (호버 시) */}
      {coachCoordMarkers && coachCoordMarkers.map((m, i) => {
        const { x, y } = toXY(m.row, m.col)
        return (
          <g key={i} pointerEvents="none">
            <circle cx={x} cy={y} r={13} fill="rgba(217,119,6,0.88)" stroke="#78350f" strokeWidth={1.5} />
            <text x={x} y={y + 5} textAnchor="middle" fontSize={12} fontWeight="bold" fill="white">
              {m.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
