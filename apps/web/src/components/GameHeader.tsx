'use client'

interface GameHeaderProps {
  moveCount: number
  blackTimeMs: number
  whiteTimeMs: number
  currentPlayer: 1 | 2
  isAiThinking: boolean
  gamePhase: string
  mode?: 'AI_VS_HUMAN' | 'HUMAN_VS_HUMAN_LOCAL'
}

function msToStr(ms: number): string {
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

export function GameHeader({
  moveCount,
  blackTimeMs,
  whiteTimeMs,
  currentPlayer,
  isAiThinking,
  gamePhase,
  mode = 'AI_VS_HUMAN',
}: GameHeaderProps) {
  const phaseLabel: Record<string, string> = {
    PLAYING: '',
    COACH_PAUSE: '사범 개입 중',
    ANSWERING: '답변 중',
    FINISHED: '대국 종료',
  }

  const isPvp = mode === 'HUMAN_VS_HUMAN_LOCAL'
  const blackLabel = isPvp ? '⚫ 흑' : '⚫ 흑(당신)'
  const whiteLabel = isPvp ? '⚪ 백' : '⚪ 백(AI)'

  return (
    <div className="flex flex-col items-center gap-2 w-full max-w-lg">
      {isPvp && gamePhase === 'PLAYING' && (
        <div className={`px-4 py-1.5 rounded-full text-sm font-semibold shadow ${
          currentPlayer === 1 ? 'bg-gray-900 text-white' : 'bg-white text-gray-900 border border-gray-300'
        }`}>
          {currentPlayer === 1 ? '흑 차례' : '백 차례'}
        </div>
      )}
      <div className="flex items-center justify-between w-full bg-white rounded-lg shadow px-4 py-2 text-sm">
        {/* 흑 */}
        <div className={`flex flex-col items-center ${currentPlayer === 1 ? 'font-bold text-gray-900' : 'text-gray-400'}`}>
          <span className="text-base">{blackLabel}</span>
          <span className="font-mono">{msToStr(blackTimeMs)}</span>
        </div>

        {/* 중앙 */}
        <div className="flex flex-col items-center gap-0.5">
          <span className="text-gray-600">{moveCount}수</span>
          {gamePhase !== 'PLAYING' && (
            <span className="text-amber-600 text-xs">{phaseLabel[gamePhase] ?? gamePhase}</span>
          )}
          {isAiThinking && <span className="text-blue-500 text-xs animate-pulse">AI 생각 중…</span>}
        </div>

        {/* 백 */}
        <div className={`flex flex-col items-center ${currentPlayer === 2 ? 'font-bold text-gray-900' : 'text-gray-400'}`}>
          <span className="text-base">{whiteLabel}</span>
          <span className="font-mono">{msToStr(whiteTimeMs)}</span>
        </div>
      </div>
    </div>
  )
}
