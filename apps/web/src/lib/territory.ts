export interface TerritoryResult {
  black: [number, number][]
  white: [number, number][]
  dame: [number, number][]
}

const BOARD_SIZE = 19

function neighbors(row: number, col: number): [number, number][] {
  const result: [number, number][] = []
  if (row > 0) result.push([row - 1, col])
  if (row < BOARD_SIZE - 1) result.push([row + 1, col])
  if (col > 0) result.push([row, col - 1])
  if (col < BOARD_SIZE - 1) result.push([row, col + 1])
  return result
}

export function computeTerritory(board: number[][]): TerritoryResult {
  const visited = new Set<string>()
  const black: [number, number][] = []
  const white: [number, number][] = []
  const dame: [number, number][] = []

  for (let r = 0; r < BOARD_SIZE; r++) {
    for (let c = 0; c < BOARD_SIZE; c++) {
      if (board[r][c] !== 0 || visited.has(`${r},${c}`)) continue

      const region: [number, number][] = []
      const queue: [number, number][] = [[r, c]]
      let touchesBlack = false
      let touchesWhite = false

      while (queue.length > 0) {
        const [qr, qc] = queue.shift()!
        const key = `${qr},${qc}`
        if (visited.has(key)) continue
        visited.add(key)
        region.push([qr, qc])

        for (const [nr, nc] of neighbors(qr, qc)) {
          if (board[nr][nc] === 0 && !visited.has(`${nr},${nc}`)) {
            queue.push([nr, nc])
          } else if (board[nr][nc] === 1) {
            touchesBlack = true
          } else if (board[nr][nc] === 2) {
            touchesWhite = true
          }
        }
      }

      if (touchesBlack && !touchesWhite) {
        black.push(...region)
      } else if (touchesWhite && !touchesBlack) {
        white.push(...region)
      } else {
        dame.push(...region)
      }
    }
  }

  return { black, white, dame }
}
