'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@/store/authStore'
import { deleteAccountApi } from '@/lib/auth'

export default function SettingsPage() {
  const router = useRouter()
  const { user, hydrated, hydrate, logout } = useAuthStore()

  const [showConfirm, setShowConfirm] = useState(false)
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => { hydrate() }, [hydrate])

  useEffect(() => {
    if (hydrated && !user) router.replace('/login')
  }, [hydrated, user, router])

  async function handleDelete() {
    if (!user) return
    setError('')
    setLoading(true)
    try {
      await deleteAccountApi(user.accessToken, password)
      logout()
      router.push('/login')
    } catch (e) {
      setError(e instanceof Error ? e.message : '오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  if (!hydrated || !user) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-gray-800">수담</Link>
        <span className="text-sm text-gray-600">{user.nickname || user.email}</span>
      </header>

      <main className="max-w-lg mx-auto px-6 py-10">
        <div className="flex items-center gap-2 mb-8">
          <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">대시보드</Link>
          <span className="text-gray-300">/</span>
          <span className="text-sm text-gray-800 font-medium">설정</span>
        </div>

        <h1 className="text-xl font-semibold text-gray-800 mb-8">계정 설정</h1>

        <section className="bg-white rounded-xl shadow-sm border border-red-100 p-6">
          <h2 className="text-base font-semibold text-red-600 mb-1">계정 탈퇴</h2>
          <p className="text-sm text-gray-500 mb-4">
            탈퇴하면 계정과 대국 기록에 더 이상 접근할 수 없습니다.
          </p>

          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="text-sm text-red-500 border border-red-300 hover:bg-red-50 px-4 py-2 rounded-lg transition"
            >
              탈퇴하기
            </button>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-700 font-medium">
                본인 확인을 위해 현재 비밀번호를 입력해 주세요.
              </p>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
              />
              {error && <p className="text-sm text-red-500">{error}</p>}
              <div className="flex gap-3">
                <button
                  onClick={handleDelete}
                  disabled={loading || !password}
                  className="text-sm bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition"
                >
                  {loading ? '처리 중…' : '탈퇴 확인'}
                </button>
                <button
                  onClick={() => { setShowConfirm(false); setPassword(''); setError('') }}
                  className="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 transition"
                >
                  취소
                </button>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
