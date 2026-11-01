const GAME_SERVER = process.env.NEXT_PUBLIC_GAME_SERVER_URL ?? 'http://localhost:8080'

export interface AuthUser {
  userId: string
  email: string
  nickname: string
  accessToken: string
  refreshToken: string
}

export async function signup(email: string, password: string, nickname: string): Promise<AuthUser> {
  const res = await fetch(`${GAME_SERVER}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, nickname }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.message ?? `Signup failed: ${res.status}`)
  }
  const data = await res.json()
  return { userId: data.userId, email: data.email, nickname: data.nickname ?? '',
           accessToken: data.accessToken, refreshToken: data.refreshToken }
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await fetch(`${GAME_SERVER}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    throw new Error('이메일 또는 비밀번호가 올바르지 않습니다.')
  }
  const data = await res.json()
  return { userId: data.userId, email: data.email, nickname: data.nickname ?? '',
           accessToken: data.accessToken, refreshToken: data.refreshToken }
}

export async function refreshAccessToken(refreshToken: string): Promise<AuthUser> {
  const res = await fetch(`${GAME_SERVER}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken }),
  })
  if (!res.ok) throw new Error('Token refresh failed')
  const data = await res.json()
  return { userId: data.userId, email: data.email, nickname: data.nickname ?? '',
           accessToken: data.accessToken, refreshToken: data.refreshToken }
}

export async function logoutApi(accessToken: string): Promise<void> {
  await fetch(`${GAME_SERVER}/api/auth/logout`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export function saveAuth(user: AuthUser): void {
  localStorage.setItem('auth', JSON.stringify(user))
  // middleware에서 읽을 수 있도록 JS-accessible 쿠키에도 저장 (토큰 자체는 담지 않음)
  document.cookie = `auth_present=1; path=/; SameSite=Strict; max-age=604800`
}

export function loadAuth(): AuthUser | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = localStorage.getItem('auth')
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

export function clearAuth(): void {
  localStorage.removeItem('auth')
  document.cookie = 'auth_present=; path=/; max-age=0'
}
