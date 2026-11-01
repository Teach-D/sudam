'use client'

import { useCallback, useEffect, useState } from 'react'

const GAME_SERVER = process.env.NEXT_PUBLIC_GAME_SERVER_URL ?? 'http://localhost:8080'

interface PendingIntervention {
  id: string
  gameId: string
  moveNumber: number
  reasonType: string
  scoreDrop: number
  draftText: string
  status: string
  createdAt: string
}

interface PendingQuestion {
  id: number
  gameId: string
  content: string
  read: boolean
  createdAt: string
}

const REASON_LABELS: Record<string, string> = {
  life_death: '대마 생사',
  cut_left: '끊김',
  missed_attack: '약한 돌 공격',
  missed_big_point: '큰 자리',
  endgame_sente: '끝내기 선수',
}

export default function OperatorPage() {
  const [interventions, setInterventions] = useState<PendingIntervention[]>([])
  const [questions, setQuestions] = useState<PendingQuestion[]>([])
  const [editTexts, setEditTexts] = useState<Record<string, string>>({})
  const [replyTexts, setReplyTexts] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [ivRes, qRes] = await Promise.all([
        fetch(`${GAME_SERVER}/api/operator/interventions`),
        fetch(`${GAME_SERVER}/api/operator/questions`),
      ])
      if (ivRes.ok) setInterventions(await ivRes.json())
      if (qRes.ok) setQuestions(await qRes.json())
    } catch {
      // server unavailable
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 5000)
    return () => clearInterval(id)
  }, [refresh])

  async function sendIntervention(iv: PendingIntervention) {
    const text = editTexts[iv.id] ?? iv.draftText
    if (!text.trim()) return
    setLoading(true)
    try {
      await fetch(`${GAME_SERVER}/api/operator/interventions/${iv.id}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      await refresh()
    } finally {
      setLoading(false)
    }
  }

  async function skipIntervention(id: string) {
    await fetch(`${GAME_SERVER}/api/operator/interventions/${id}/skip`, { method: 'POST' })
    await refresh()
  }

  async function replyQuestion(q: PendingQuestion) {
    const content = replyTexts[q.id]?.trim()
    if (!content) return
    setLoading(true)
    try {
      await fetch(`${GAME_SERVER}/api/operator/questions/${q.id}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      setReplyTexts((p) => ({ ...p, [q.id]: '' }))
      await refresh()
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="max-w-4xl mx-auto p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">운영자 콘솔</h1>
        <button
          onClick={refresh}
          className="text-sm text-blue-600 hover:underline"
        >
          새로 고침
        </button>
      </div>

      {/* Pending interventions */}
      <section>
        <h2 className="font-semibold text-gray-700 mb-3">
          개입 검수 대기 ({interventions.length})
        </h2>
        {interventions.length === 0 && (
          <p className="text-gray-400 text-sm">대기 중인 개입이 없습니다.</p>
        )}
        <div className="flex flex-col gap-4">
          {interventions.map((iv) => (
            <div key={iv.id} className="bg-white rounded-lg shadow p-4 flex flex-col gap-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-amber-700">
                  {REASON_LABELS[iv.reasonType] ?? iv.reasonType}
                </span>
                <span className="text-gray-400">
                  {iv.moveNumber}수 · {iv.scoreDrop.toFixed(1)}집 손해
                </span>
              </div>
              <textarea
                className="w-full border rounded p-2 text-sm resize-none"
                rows={3}
                value={editTexts[iv.id] ?? iv.draftText}
                onChange={(e) =>
                  setEditTexts((p) => ({ ...p, [iv.id]: e.target.value }))
                }
              />
              <div className="flex gap-2">
                <button
                  onClick={() => sendIntervention(iv)}
                  disabled={loading}
                  className="flex-1 py-1.5 bg-amber-600 text-white rounded text-sm hover:bg-amber-700 disabled:opacity-40 transition"
                >
                  전송
                </button>
                <button
                  onClick={() => skipIntervention(iv.id)}
                  className="px-4 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50 transition"
                >
                  건너뜀
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* User questions */}
      <section>
        <h2 className="font-semibold text-gray-700 mb-3">
          사용자 질문 ({questions.length})
        </h2>
        {questions.length === 0 && (
          <p className="text-gray-400 text-sm">미읽은 질문이 없습니다.</p>
        )}
        <div className="flex flex-col gap-4">
          {questions.map((q) => (
            <div key={q.id} className="bg-white rounded-lg shadow p-4 flex flex-col gap-3">
              <div className="bg-blue-50 rounded p-2 text-sm text-gray-700">{q.content}</div>
              <textarea
                className="w-full border rounded p-2 text-sm resize-none"
                rows={2}
                placeholder="답변 입력..."
                value={replyTexts[q.id] ?? ''}
                onChange={(e) =>
                  setReplyTexts((p) => ({ ...p, [q.id]: e.target.value }))
                }
              />
              <button
                onClick={() => replyQuestion(q)}
                disabled={loading || !replyTexts[q.id]?.trim()}
                className="py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-40 transition"
              >
                답변 전송
              </button>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
