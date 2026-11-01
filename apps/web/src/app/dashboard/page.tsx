'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@/store/authStore'
import { fetchMyGames, sgfDownloadUrl, type GameSummary } from '@/lib/api'
import { logoutApi } from '@/lib/auth'

function formatDate(iso: string | null) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function modeLabel(mode: string) {
  return mode === 'AI_VS_HUMAN' ? 'AI 대국' : '두 사람 대국'
}

export default function DashboardPage() {
  const router = useRouter()
  const { user, hydrated, hydrate, logout } = useAuthStore()
  const [games, setGames] = useState<GameSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => { hydrate() }, [hydrate])

  useEffect(() => {
    if (!hydrated) return
    if (!user) { router.replace('/login'); return }
    fetchMyGames()
      .then(setGames)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [hydrated, user, router])

  async function handleLogout() {
    if (user) await logoutApi(user.accessToken).catch(() => {})
    logout()
    router.push('/')
  }

  if (!hydrated || !user) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-gray-800">수담</Link>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user.nickname || user.email}</span>
          <button
            onClick={handleLogout}
            className="text-sm text-gray-500 hover:text-gray-800 transition"
          >
            로그아웃
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-800">내 대국 기록</h2>
          <Link
            href="/"
            className="bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            새 대국 시작
          </Link>
        </div>

        {loading && <p className="text-gray-500 text-sm">불러오는 중…</p>}
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {!loading && !error && games.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <p className="text-lg">아직 기록된 대국이 없습니다.</p>
            <Link href="/" className="mt-4 inline-block text-amber-600 hover:underline text-sm">
              첫 대국을 시작해 보세요
            </Link>
          </div>
        )}

        {games.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">날짜</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">종류</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">수</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">결과</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">상태</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {games.map((g) => (
                  <tr key={g.id} className="hover:bg-gray-50 transition">
                    <td className="px-4 py-3 text-gray-700">{formatDate(g.createdAt)}</td>
                    <td className="px-4 py-3 text-gray-700">{modeLabel(g.mode)}</td>
                    <td className="px-4 py-3 text-gray-700">{g.moveCount}수</td>
                    <td className="px-4 py-3 font-medium text-gray-800">{g.result ?? '-'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        g.status === 'FINISHED'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {g.status === 'FINISHED' ? '완료' : '진행 중'}
                      </span>
                    </td>
                    <td className="px-4 py-3 flex gap-2 justify-end">
                      <Link
                        href={`/games/${g.id}/replay`}
                        className="text-amber-600 hover:underline text-xs font-medium"
                      >
                        다시두기
                      </Link>
                      <a
                        href={sgfDownloadUrl(g.id)}
                        download={`game-${g.id}.sgf`}
                        className="text-gray-500 hover:text-gray-700 text-xs font-medium"
                      >
                        SGF
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
