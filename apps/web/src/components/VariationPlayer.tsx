'use client'

interface VariationMove {
  row: number
  col: number
  color: string
  label: string
}

interface VariationPlayerProps {
  moves: VariationMove[]
  currentStep: number               // 0 = 없음, n = n번째까지 표시
  onStep: (step: number) => void
  onClose: () => void
}

export function VariationPlayer({ moves, currentStep, onStep, onClose }: VariationPlayerProps) {
  if (moves.length === 0) return null

  return (
    <div className="bg-white rounded-lg border border-amber-200 p-3 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-amber-700">수순 재생</span>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-xs"
        >
          ✕
        </button>
      </div>

      {/* 수순 단계 버튼 */}
      <div className="flex gap-1 flex-wrap mb-2">
        {moves.map((mv, i) => (
          <button
            key={i}
            onClick={() => onStep(i + 1)}
            className={`w-8 h-8 rounded-full text-sm font-bold border transition ${
              i + 1 <= currentStep
                ? 'bg-amber-600 text-white border-amber-700'
                : 'bg-gray-100 text-gray-500 border-gray-300 hover:bg-amber-50'
            }`}
          >
            {mv.label}
          </button>
        ))}
      </div>

      {/* 이전 / 다음 */}
      <div className="flex gap-2">
        <button
          onClick={() => onStep(Math.max(0, currentStep - 1))}
          disabled={currentStep === 0}
          className="flex-1 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-40 transition"
        >
          ◀ 이전
        </button>
        <button
          onClick={() => onStep(Math.min(moves.length, currentStep + 1))}
          disabled={currentStep >= moves.length}
          className="flex-1 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-40 transition"
        >
          다음 ▶
        </button>
      </div>

      {/* 현재 수 설명 */}
      {currentStep > 0 && currentStep <= moves.length && (
        <p className="text-xs text-gray-600 mt-2 text-center">
          {moves[currentStep - 1].label} — {moves[currentStep - 1].color === 'B' ? '흑' : '백'} 착수
        </p>
      )}
    </div>
  )
}
