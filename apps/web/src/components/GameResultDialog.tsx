'use client'

import type { GameResult, MoveRecord } from '@/store/gameStore'

interface GameResultDialogProps {
  result: GameResult
  moveHistory: MoveRecord[]
  komi: number
  onClose: () => void
  onReview: () => void
}

function buildSgf(moveHistory: MoveRecord[], komi: number, result: GameResult): string {
  const movesStr = moveHistory
    .filter((m) => !m.retracted)
    .map((m) => {
      const col = String.fromCharCode('a'.charCodeAt(0) + m.col)
      const row = String.fromCharCode('a'.charCodeAt(0) + m.row)
      const color = m.color === 1 ? 'B' : 'W'
      return `;${color}[${col}${row}]`
    })
    .join('')
  return `(;FF[4]GM[1]SZ[19]KM[${komi}]PB[사용자]PW[수담 AI]RE[${result.result}]${movesStr})`
}

function downloadSgf(moveHistory: MoveRecord[], komi: number, result: GameResult) {
  const content = buildSgf(moveHistory, komi, result)
  const blob = new Blob([content], { type: 'application/x-go-sgf' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sudam_${new Date().toISOString().slice(0, 10)}.sgf`
  a.click()
  URL.revokeObjectURL(url)
}

export function GameResultDialog({
  result,
  moveHistory,
  komi,
  onClose,
  onReview,
}: GameResultDialogProps) {
  const isBlackWin = result.result.startsWith('B')

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl p-8 flex flex-col items-center gap-4 w-80">
        <div className="text-4xl">{isBlackWin ? '⚫' : '⚪'}</div>
        <h2 className="text-2xl font-bold text-gray-800">{result.result}</h2>
        <p className="text-gray-500 text-sm">
          {isBlackWin ? '흑(당신)' : '백(AI)'} 승
        </p>
        <div className="flex gap-8 text-sm text-gray-600">
          <div className="flex flex-col items-center">
            <span className="font-medium">흑</span>
            <span>{result.blackScore.toFixed(1)}</span>
          </div>
          <div className="flex flex-col items-center">
            <span className="font-medium">백</span>
            <span>{result.whiteScore.toFixed(1)}</span>
          </div>
        </div>

        <div className="flex flex-col gap-2 w-full mt-2">
          <button
            onClick={onReview}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
          >
            AI 해설 보기
          </button>
          <button
            onClick={() => downloadSgf(moveHistory, komi, result)}
            className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition text-sm font-medium"
          >
            기보 저장 (SGF)
          </button>
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-amber-700 text-white rounded-lg hover:bg-amber-800 transition text-sm font-medium"
          >
            새 대국
          </button>
        </div>
      </div>
    </div>
  )
}
