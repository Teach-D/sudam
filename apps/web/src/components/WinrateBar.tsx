'use client'

interface WinrateBarProps {
  blackWinrate: number   // 0.0–1.0
  scoreLead: number      // positive = black leading
  loading?: boolean      // KataGo 분석 대기 중 — 이전 값을 유지한 채 흐려짐 + 스피너 표시
}

export function WinrateBar({ blackWinrate, scoreLead, loading = false }: WinrateBarProps) {
  const blackPct = Math.round(blackWinrate * 100)
  const whitePct = 100 - blackPct

  const leadStr =
    scoreLead === 0
      ? '동등'
      : scoreLead > 0
      ? `흑 +${scoreLead.toFixed(1)}`
      : `백 +${(-scoreLead).toFixed(1)}`

  return (
    <div className="w-full max-w-lg">
      <div className="flex text-xs text-gray-500 justify-between mb-0.5 px-0.5 items-center">
        <span>흑 {blackPct}%</span>
        <span className="font-medium text-gray-700 flex items-center gap-1">
          {leadStr}
          {loading && (
            <span
              aria-label="분석 중"
              className="inline-block w-3 h-3 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"
            />
          )}
        </span>
        <span>백 {whitePct}%</span>
      </div>
      <div
        className={`flex h-3 rounded overflow-hidden transition-opacity duration-200 ${
          loading ? 'opacity-40' : 'opacity-100'
        }`}
      >
        <div
          className="bg-gray-800 transition-all duration-500"
          style={{ width: `${blackPct}%` }}
        />
        <div
          className="bg-gray-100 border-l border-gray-300 transition-all duration-500"
          style={{ width: `${whitePct}%` }}
        />
      </div>
    </div>
  )
}
