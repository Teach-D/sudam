'use client'

import { useState, useMemo } from 'react'
import { VariationPlayer } from './VariationPlayer'
import type { CoachMessage, HintStep, VariationMove } from '@/store/gameStore'
import { splitWithCoords, extractMarkersFromSegments } from '@/lib/coordHighlight'
import type { CoordMarker } from '@/lib/coordHighlight'

const REASON_CHIPS = [
  { label: '설명이 틀림', value: 'wrong' },
  { label: '이해가 안 됨', value: 'unclear' },
  { label: '너무 김', value: 'too_long' },
  { label: '부적절함(신고)', value: 'report' },
] as const

interface RichTextProps {
  text: string
  onCoordHover?: (markers: CoordMarker[] | null) => void
}

function RichText({ text, onCoordHover }: RichTextProps) {
  const segments = useMemo(() => splitWithCoords(text), [text])
  const markers = useMemo(() => extractMarkersFromSegments(segments), [segments])

  if (markers.length === 0) return <>{text}</>

  return (
    <span onMouseLeave={() => onCoordHover?.(null)}>
      {segments.map((seg, i) =>
        seg.type === 'text' ? (
          <span key={i}>{seg.content}</span>
        ) : (
          <span
            key={i}
            className="font-mono text-amber-700 bg-amber-50 rounded px-0.5 cursor-default hover:bg-amber-100 transition-colors"
            onMouseEnter={() => onCoordHover?.(markers)}
          >
            {seg.content}{seg.marker.label}
          </span>
        ),
      )}
    </span>
  )
}

const PRESET_CHIPS = [
  { label: '다음 어디?',         text: '다음에 어디에 두면 좋을까요?' },
  { label: '이 돌 살아있어?',    text: '이 돌이 살아있나요?' },
  { label: '이 수 왜 나빠?',     text: '방금 수가 왜 나쁜가요?' },
  { label: '큰 자리 알려줘',     text: '지금 가장 큰 자리가 어디인가요?' },
  { label: '지금 끝내기 할 때?', text: '지금 끝내기를 시작할 때인가요?' },
]

interface CoachPanelProps {
  messages: CoachMessage[]
  variation: VariationMove[]
  variationStep: number
  hints: HintStep[]
  currentHintStep: number
  questionInput: string
  isCoachActive: boolean         // COACH_PAUSE 또는 ANSWERING 상태
  onVariationStep: (step: number) => void
  onCloseVariation: () => void
  onRevealHint: () => void
  onQuestionChange: (v: string) => void
  onSendQuestion: () => void
  onPresetQuestion: (text: string) => void
  onWhyAsk: () => void           // "잠깐, 이거 왜?" 버튼
  onCoordHover?: (markers: CoordMarker[] | null) => void  // 좌표 토큰 호버
  pinnedCoordLabel?: string | null  // 핀된 교차점 한국식 좌표 (e.g. "라4")
  onAskPinned?: () => void          // "여기에 두면?" 질문 전송
  onClearPin?: () => void           // 핀 해제
  // PvP(핫시트) 전용. null이면 패널 전체가 가려진다(상대 턴 보호).
  // 'open-for-black' / 'open-for-white' 는 각 색의 플레이어가 질의 세션을 연 상태.
  // AI 모드에서는 undefined로 두면 기존 UX 그대로 동작한다.
  pvpVisibility?: 'hidden' | 'open-for-black' | 'open-for-white' | 'review'
  onOpenPanel?: () => void       // "사범에게 묻기" — 현재 턴 플레이어가 패널을 연다
  onClosePanel?: () => void      // "확인" — 질의 세션 종료
  onFeedback?: (messageId: string, rating: 'up' | 'down', reason?: string) => void
  coachEnabled?: boolean
  onToggleCoach?: (v: boolean) => void
}

export function CoachPanel({
  messages,
  variation,
  variationStep,
  hints,
  currentHintStep,
  questionInput,
  isCoachActive,
  onVariationStep,
  onCloseVariation,
  onRevealHint,
  onQuestionChange,
  onSendQuestion,
  onPresetQuestion,
  onWhyAsk,
  onCoordHover,
  pinnedCoordLabel,
  onAskPinned,
  onClearPin,
  pvpVisibility,
  onOpenPanel,
  onClosePanel,
  onFeedback,
  coachEnabled = true,
  onToggleCoach,
}: CoachPanelProps) {
  const [showHints, setShowHints] = useState(false)
  const [openReasonFor, setOpenReasonFor] = useState<string | null>(null)

  function handleThumb(msg: CoachMessage, rating: 'up' | 'down') {
    if (msg.rating === rating) return
    onFeedback?.(msg.id, rating)
    setOpenReasonFor(rating === 'down' ? msg.id : null)
  }

  function handleReason(msg: CoachMessage, reason: string) {
    onFeedback?.(msg.id, 'down', reason)
    setOpenReasonFor(null)
  }

  // 가장 최근 코치 push 또는 draft 메시지
  const lastPush = [...messages].reverse().find((m) => m.type === 'push' || m.type === 'draft')

  // PvP: 패널이 닫혀있으면 "사범에게 묻기" 버튼만 노출. 상대 턴에 정보 유출 방지.
  if (pvpVisibility === 'hidden') {
    return (
      <div className="flex flex-col gap-3 w-72">
        <div className="bg-white rounded-lg shadow p-4 flex flex-col items-center gap-3">
          <p className="text-xs text-gray-500 text-center">
            상대 턴 중에는 사범 패널이 가려집니다.
          </p>
          {onOpenPanel && (
            <button
              onClick={onOpenPanel}
              className="w-full py-2 bg-amber-600 text-white rounded text-sm hover:bg-amber-700 transition"
            >
              사범에게 묻기 (내 턴)
            </button>
          )}
        </div>
      </div>
    )
  }

  const panelLabel =
    pvpVisibility === 'open-for-black'
      ? '⚫ 흑 전용'
      : pvpVisibility === 'open-for-white'
      ? '⚪ 백 전용'
      : pvpVisibility === 'review'
      ? '복기 — 양쪽 공개'
      : null

  return (
    <div className="flex flex-col gap-3 w-72">
      {onToggleCoach && (
        <div className="flex items-center justify-between bg-white border border-gray-200 rounded px-3 py-1.5 text-xs shadow-sm">
          <span className="text-gray-600">사범 알림</span>
          <button
            onClick={() => onToggleCoach(!coachEnabled)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${coachEnabled ? 'bg-amber-500' : 'bg-gray-300'}`}
          >
            <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${coachEnabled ? 'translate-x-5' : 'translate-x-1'}`} />
          </button>
        </div>
      )}
      {panelLabel && (
        <div className="flex items-center justify-between bg-amber-100 border border-amber-300 rounded px-2 py-1 text-xs">
          <span className="font-semibold text-amber-800">{panelLabel}</span>
          {onClosePanel && pvpVisibility !== 'review' && (
            <button
              onClick={onClosePanel}
              className="px-2 py-0.5 bg-white text-amber-800 rounded hover:bg-amber-50 transition"
            >
              확인 (닫기)
            </button>
          )}
        </div>
      )}

      {/* 사범 말풍선 */}
      {lastPush && (
        <div className="relative bg-amber-50 border border-amber-300 rounded-xl p-3 shadow-sm">
          {/* 검증 뱃지 */}
          <div className="absolute top-2 right-2">
            {lastPush.verified === true ? (
              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">✓ 검증됨</span>
            ) : lastPush.verified === false ? (
              <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">템플릿</span>
            ) : null}
          </div>
          <p className="text-sm text-amber-900 leading-relaxed pr-16">
            <RichText text={lastPush.text} onCoordHover={onCoordHover} />
          </p>

          {/* 의도 버튼 */}
          {isCoachActive && (
            <div className="flex gap-2 mt-2 flex-wrap">
              <button
                onClick={() => setShowHints(true)}
                className="text-xs px-2 py-1 bg-amber-100 hover:bg-amber-200 text-amber-800 rounded transition"
              >
                💡 힌트 보기
              </button>
              <button
                onClick={onWhyAsk}
                className="text-xs px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded border border-blue-200 transition"
              >
                {lastPush?.type === 'draft' ? '왜 나쁜 수인가요?' : '잠깐, 이거 왜?'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* 단계형 힌트 */}
      {showHints && hints.length > 0 && (
        <div className="bg-white border border-amber-200 rounded-lg p-3 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-amber-700">힌트</span>
            <button onClick={() => setShowHints(false)} className="text-gray-400 hover:text-gray-600 text-xs">✕</button>
          </div>

          {/* 공개된 힌트 단계 */}
          {hints.slice(0, currentHintStep).map((h) => (
            <div key={h.step} className="mb-2 flex gap-2 items-start">
              <span className="text-amber-600 font-bold text-sm w-5 shrink-0">{h.label}</span>
              <p className="text-sm text-gray-700">{h.text}</p>
            </div>
          ))}

          {currentHintStep < hints.length ? (
            <button
              onClick={onRevealHint}
              className="w-full mt-1 py-1.5 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 transition"
            >
              {currentHintStep === 0 ? '힌트 ① 보기' : `힌트 ${hints[currentHintStep]?.label} 보기`}
            </button>
          ) : (
            <p className="text-xs text-gray-400 text-center mt-1">힌트를 모두 확인했습니다.</p>
          )}
        </div>
      )}

      {/* 수순 재생 */}
      <VariationPlayer
        moves={variation}
        currentStep={variationStep}
        onStep={onVariationStep}
        onClose={onCloseVariation}
      />

      {/* 전체 메시지 기록 */}
      <div className="bg-white rounded-lg shadow p-3">
        <h2 className="font-semibold text-gray-700 mb-2 text-sm">메시지</h2>
        <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
          {messages.length === 0 && (
            <p className="text-gray-400 text-xs">아직 메시지가 없습니다.</p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`rounded p-2 text-sm ${
                m.type === 'push'
                  ? 'bg-amber-50 border-l-4 border-amber-500'
                  : 'bg-blue-50 border-l-4 border-blue-400'
              }`}
            >
              <RichText text={m.text} onCoordHover={onCoordHover} />
              {m.answerId != null && onFeedback && (
                <div className="mt-1.5">
                  <div className="flex gap-1 justify-end">
                    <button
                      onClick={() => handleThumb(m, 'up')}
                      title="도움이 됐어요"
                      className={`text-xs px-1.5 py-0.5 rounded transition ${
                        m.rating === 'up'
                          ? 'bg-green-100 text-green-700'
                          : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                      }`}
                    >
                      👍
                    </button>
                    <button
                      onClick={() => handleThumb(m, 'down')}
                      title="문제가 있어요"
                      className={`text-xs px-1.5 py-0.5 rounded transition ${
                        m.rating === 'down'
                          ? 'bg-red-100 text-red-600'
                          : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
                      }`}
                    >
                      👎
                    </button>
                  </div>
                  {openReasonFor === m.id && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {REASON_CHIPS.map((chip) => (
                        <button
                          key={chip.value}
                          onClick={() => handleReason(m, chip.value)}
                          className="text-xs px-2 py-0.5 bg-gray-100 hover:bg-red-50 hover:text-red-700 text-gray-600 rounded-full border border-gray-200 transition"
                        >
                          {chip.label}
                        </button>
                      ))}
                    </div>
                  )}
                  {m.feedbackReason && (
                    <p className="text-xs text-gray-400 text-right mt-0.5">
                      {REASON_CHIPS.find((c) => c.value === m.feedbackReason)?.label ?? m.feedbackReason}
                    </p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 질문하기 */}
      <div className="bg-white rounded-lg shadow p-3">
        <h2 className="font-semibold text-gray-700 mb-2 text-sm">질문하기</h2>
        <div className="flex flex-wrap gap-1 mb-2">
          {PRESET_CHIPS.map((c) => (
            <button
              key={c.label}
              onClick={() => onPresetQuestion(c.text)}
              className="text-xs px-2 py-1 bg-gray-100 hover:bg-amber-100 text-gray-600 hover:text-amber-800 rounded-full border border-gray-200 transition"
            >
              {c.label}
            </button>
          ))}
        </div>

        {isCoachActive && pinnedCoordLabel && (
          <div className="flex items-center gap-2 mb-2 bg-blue-50 border border-blue-200 rounded-lg px-2 py-1.5">
            <span className="text-xs text-blue-600 font-mono shrink-0">📍 {pinnedCoordLabel}</span>
            <button
              onClick={onAskPinned}
              className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
            >
              여기에 두면?
            </button>
            <button
              onClick={onClearPin}
              className="ml-auto text-gray-400 hover:text-gray-600 text-xs leading-none"
            >
              ✕
            </button>
          </div>
        )}
        <textarea
          className="w-full border rounded p-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-amber-400"
          rows={2}
          placeholder="사범에게 질문을 입력하세요"
          value={questionInput}
          onChange={(e) => onQuestionChange(e.target.value)}
        />
        <button
          onClick={onSendQuestion}
          disabled={!questionInput.trim()}
          className="mt-2 w-full py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-40 transition"
        >
          전송
        </button>
      </div>
    </div>
  )
}
