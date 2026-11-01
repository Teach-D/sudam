'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { GoBoard } from '@/components/GoBoard'
import { replayBoard } from '@/lib/boardReplay'
import { sgfDownloadUrl } from '@/lib/api'

const GAME_SERVER = process.env.NEXT_PUBLIC_GAME_SERVER_URL ?? 'http://localhost:8080'

interface MoveData {
  moveNumber: number
  color: 'BLACK' | 'WHITE'
  row: number | null
  col: number | null
  retracted: boolean
}

export default function ReplayPage({ params }: { params: { id: string } }) {
  const { id } = params
  const [moves, setMoves] = useState<MoveData[]>([])
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${GAME_SERVER}/api/games/${id}/moves`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`)
        return r.json()
      })
      .then((data: MoveData[]) => {
        setMoves(data)
        setStep(data.filter((m) => !m.retracted).length)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  const activeMoves = moves.filter((m) => !m.retracted)

  // pass moves (row=null) are excluded from board replay but counted in step
  const boardMoves = activeMoves.slice(0, step)
    .filter((m) => m.row !== null)
    .map((m, i) => ({
      row: m.row!,
      col: m.col!,
      color: (m.color === 'BLACK' ? 1 : 2) as 1 | 2,
      moveNumber: i + 1,
      retracted: false,
    }))

  const boardState = replayBoard(boardMoves, boardMoves.length)

  const currentMove = activeMoves[step - 1]

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <Link href="/dashboard" className="text-gray-500 hover:text-gray-800 text-sm transition">
          ← 대국 목록
        </Link>
        <span className="text-lg font-semibold text-gray-800">기보 다시두기</span>
        <div className="ml-auto">
          <a
            href={sgfDownloadUrl(id)}
            download={`game-${id}.sgf`}
            className="text-sm text-amber-600 hover:underline"
          >
            SGF 다운로드
          </a>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 flex flex-col lg:flex-row gap-8">
        <div className="flex-1">
          {loading && <div className="text-gray-400 text-sm">불러오는 중…</div>}
          {error && <div className="text-red-500 text-sm">오류: {error}</div>}
          {!loading && !error && (
            <GoBoard
              board={boardState}
              moveHistory={boardMoves}
              currentPlayer={1}
              onPlace={() => {}}
              disabled={true}
            />
          )}
        </div>

        <div className="w-full lg:w-64 space-y-4">
          <div className="bg-white rounded-xl shadow-sm p-4">
            <p className="text-sm text-gray-500 mb-1">현재 수</p>
            <p className="text-2xl font-bold text-gray-800">{step} / {activeMoves.length}</p>
            {currentMove && (
              <p className="text-sm text-gray-500 mt-1">
                {currentMove.color === 'BLACK' ? '흑' : '백'}
                {currentMove.row !== null ? ` (${currentMove.row + 1}, ${currentMove.col! + 1})` : ' 패스'}
              </p>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm p-4 space-y-2">
            <div className="flex gap-2">
              <button
                onClick={() => setStep(0)}
                disabled={step === 0}
                className="flex-1 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition"
              >
                처음
              </button>
              <button
                onClick={() => setStep(activeMoves.length)}
                disabled={step === activeMoves.length}
                className="flex-1 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition"
              >
                끝
              </button>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
                className="flex-1 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg disabled:opacity-40 transition font-medium"
              >
                ← 이전
              </button>
              <button
                onClick={() => setStep((s) => Math.min(activeMoves.length, s + 1))}
                disabled={step === activeMoves.length}
                className="flex-1 py-2 text-sm bg-amber-500 hover:bg-amber-600 text-white rounded-lg disabled:opacity-40 transition font-medium"
              >
                다음 →
              </button>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-4">
            <input
              type="range"
              min={0}
              max={activeMoves.length}
              value={step}
              onChange={(e) => setStep(Number(e.target.value))}
              className="w-full accent-amber-500"
            />
          </div>
        </div>
      </main>
    </div>
  )
}
