'use client'

import { useEffect } from 'react'

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
  hidden: boolean
  onHideToggle: () => void
}

export function VariationPlayer({ moves, currentStep, onStep, onClose, hidden, onHideToggle }: VariationPlayerProps) {
  if (moves.length === 0) return null

  // ← → 키보드로 수순 탐색
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') onStep(Math.max(0, currentStep - 1))
      else if (e.key === 'ArrowRight') onStep(Math.min(moves.length, currentStep + 1))
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [currentStep, moves.length, onStep])

  const currentMove = currentStep > 0 && currentStep <= moves.length ? moves[currentStep - 1] : null

  return (
    <div className="bg-white rounded-lg border border-amber-200 p-3 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-amber-700">수순 재생</span>
        <div className="flex items-center gap-1">
          <button
            onClick={onHideToggle}
            title={hidden ? '보드에 표시' : '보드에서 숨기기'}
            className="text-xs px-1.5 py-0.5 rounded bg-gray-100 hover:bg-gray-200 text-gray-500 transition"
          >
            {hidden ? '보이기' : '숨기기'}
          </button>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xs ml-1"
          >
            ✕
          </button>
        </div>
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

      {/* ◀◀ 이전 다음 ▶▶ */}
      <div className="flex gap-1">
        <button
          onClick={() => onStep(0)}
          disabled={currentStep === 0}
          className="flex-none px-1.5 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-40 transition"
          title="처음으로"
        >
          ◀◀
        </button>
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
        <button
          onClick={() => onStep(moves.length)}
          disabled={currentStep >= moves.length}
          className="flex-none px-1.5 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-40 transition"
          title="마지막으로"
        >
          ▶▶
        </button>
      </div>

      {/* 현재 수 설명 */}
      <div className="mt-2 text-xs text-center h-4">
        {currentMove ? (
          <span className="text-gray-600">
            {currentMove.label} — {currentMove.color === 'B' ? '흑' : '백'} {currentStep}번째 수
          </span>
        ) : (
          <span className="text-gray-400">← → 키로 이동</span>
        )}
      </div>

      {hidden && (
        <p className="text-xs text-gray-400 text-center mt-1">보드에서 숨김</p>
      )}
    </div>
  )
}
