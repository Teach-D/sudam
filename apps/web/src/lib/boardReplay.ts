import type { MoveRecord, BoardState } from '@/store/gameStore'

const BOARD_SIZE = 19

function neighbors(row: number, col: number): [number, number][] {
  const result: [number, number][] = []
  if (row > 0) result.push([row - 1, col])
  if (row < BOARD_SIZE - 1) result.push([row + 1, col])
  if (col > 0) result.push([row, col - 1])
  if (col < BOARD_SIZE - 1) result.push([row, col + 1])
  return result
}

function getGroup(board: BoardState, row: number, col: number): [number, number][] {
  const color = board[row][col]
  if (color === 0) return []
  const visited = new Set<string>()
  const stack: [number, number][] = [[row, col]]
  const group: [number, number][] = []
  while (stack.length > 0) {
    const [r, c] = stack.pop()!
    const key = `${r},${c}`
    if (visited.has(key)) continue
    visited.add(key)
    group.push([r, c])
    for (const [nr, nc] of neighbors(r, c)) {
      if (board[nr][nc] === color && !visited.has(`${nr},${nc}`)) {
        stack.push([nr, nc])
      }
    }
  }
  return group
}

function hasLiberty(board: BoardState, group: [number, number][]): boolean {
  for (const [r, c] of group) {
    for (const [nr, nc] of neighbors(r, c)) {
      if (board[nr][nc] === 0) return true
    }
  }
  return false
}

/**
 * moveHistory의 첫 targetStep 수까지 재생한 보드 상태를 반환한다.
 * retracted 수는 건너뛴다.
 */
export function replayBoard(moveHistory: MoveRecord[], targetStep: number): BoardState {
  const board: BoardState = Array.from({ length: BOARD_SIZE }, () => new Array(BOARD_SIZE).fill(0))
  const active = moveHistory.filter((m) => !m.retracted).slice(0, targetStep)

  for (const m of active) {
    board[m.row][m.col] = m.color
    const opponent = m.color === 1 ? 2 : 1
    for (const [nr, nc] of neighbors(m.row, m.col)) {
      if (board[nr][nc] === opponent) {
        const grp = getGroup(board, nr, nc)
        if (!hasLiberty(board, grp)) {
          for (const [gr, gc] of grp) board[gr][gc] = 0
        }
      }
    }
  }
  return board
}
