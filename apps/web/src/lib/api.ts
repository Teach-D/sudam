const AI_SERVICE = process.env.NEXT_PUBLIC_AI_SERVICE_URL ?? 'http://localhost:8000'
const GAME_SERVER = process.env.NEXT_PUBLIC_GAME_SERVER_URL ?? 'http://localhost:8080'

async function authHeader(): Promise<Record<string, string>> {
  if (typeof window === 'undefined') return {}
  try {
    const raw = localStorage.getItem('auth')
    if (!raw) return {}
    const auth = JSON.parse(raw) as import('@/lib/auth').AuthUser
    let { accessToken } = auth

    // Decode JWT exp claim to check expiry proactively
    // JWT uses base64url (- and _ instead of + and /); atob() only handles standard base64
    const parts = accessToken.split('.')
    if (parts.length === 3) {
      const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
      const padded = b64.padEnd(Math.ceil(b64.length / 4) * 4, '=')
      const payload = JSON.parse(atob(padded))
      if (payload.exp * 1000 < Date.now()) {
        // Token expired — try to refresh silently
        const { refreshAccessToken, saveAuth } = await import('@/lib/auth')
        const refreshed = await refreshAccessToken(auth.refreshToken)
        saveAuth(refreshed)
        accessToken = refreshed.accessToken
      }
    }
    return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
  } catch {
    return {}
  }
}

export type BoardState = number[][] // 0=empty, 1=black, 2=white
export type GtpMove = [string, string] // ["B","D4"]

// row=0이 보드 위, GTP는 row=1이 아래. 'I'는 건너뛴다.
const GTP_COLS = 'ABCDEFGHJKLMNOPQRST'
export function rowColToGtp(row: number, col: number, boardSize = 19): string {
  return `${GTP_COLS[col]}${boardSize - row}`
}
export function moveHistoryToGtp(
  moves: Array<{ row: number; col: number; color: 1 | 2; retracted?: boolean }>,
  boardSize = 19,
): GtpMove[] {
  return moves
    .filter((m) => !m.retracted)
    .map((m) => [m.color === 1 ? 'B' : 'W', rowColToGtp(m.row, m.col, boardSize)])
}

// ── AI Service ───────────────────────────────────────────────────────────────

export async function fetchAiMove(
  gameId: string,
  boardState: BoardState,
  moveNumber: number,
  color: 'B' | 'W',
  moveHistory: GtpMove[] = [],
  aiRank?: string,
): Promise<{ row: number; col: number; move_str: string; is_pass: boolean; score_lead: number; winrate: number; score_stdev: number }> {
  const res = await fetch(`${AI_SERVICE}/api/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      game_id: gameId,
      board_state: boardState,
      move_number: moveNumber,
      color,
      move_history: moveHistory,
      ai_rank: aiRank ?? null,
    }),
  })
  if (!res.ok) throw new Error(`AI move error: ${res.status}`)
  return res.json()
}

export async function checkIntervention(payload: {
  game_id: string
  move_number: number
  score_before: number
  score_after: number
  winrate_before: number
  winrate_after: number
  score_stdev?: number
  interventions_so_far: number
  last_intervention_move: number
  board_state?: BoardState
  played_row?: number
  played_col?: number
  color_that_moved?: 'B' | 'W'
}) {
  const res = await fetch(`${AI_SERVICE}/api/intervention/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Intervention check error: ${res.status}`)
  return res.json() as Promise<{
    triggered: boolean
    score: number
    reason_type: string | null
    score_drop: number
  }>
}

export async function fetchDraft(payload: {
  game_id: string
  board_state: BoardState
  reason_type: string
  score_drop: number
  move_number: number
  color_that_moved: 'B' | 'W'
}) {
  const res = await fetch(`${AI_SERVICE}/api/intervention/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Draft error: ${res.status}`)
  return res.json() as Promise<{ draft_text: string; reason_type: string }>
}

// ── Game Server ───────────────────────────────────────────────────────────────

export type GameMode = 'AI_VS_HUMAN' | 'HUMAN_VS_HUMAN_LOCAL'

export async function createGame(
  boardSize = 19,
  komi = 6.5,
  mode: GameMode = 'AI_VS_HUMAN',
  aiRank?: string,
) {
  const res = await fetch(`${GAME_SERVER}/api/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await authHeader()) },
    body: JSON.stringify({ boardSize, komi, mode, aiRank: aiRank ?? null }),
  })
  if (!res.ok) throw new Error(`Create game error: ${res.status}`)
  return res.json() as Promise<{ id: string; status: string; mode: string; moveCount: number; aiRank: string | null }>
}

export async function logMove(
  gameId: string,
  color: 'BLACK' | 'WHITE',
  row: number | null,
  col: number | null,
  source: 'HUMAN' | 'AI',
  scoreLead?: number,
  winrate?: number,
) {
  const res = await fetch(`${GAME_SERVER}/api/games/${gameId}/moves`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ color, row, col, source, scoreLead, winrate }),
  })
  if (!res.ok) throw new Error(`Log move error: ${res.status}`)
  return res.json()
}

export async function postUserQuestion(gameId: string, content: string) {
  const res = await fetch(`${GAME_SERVER}/api/operator/games/${gameId}/questions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error(`Question error: ${res.status}`)
  return res.json()
}

export async function getGameMessages(gameId: string) {
  const res = await fetch(`${GAME_SERVER}/api/operator/games/${gameId}/messages`)
  if (!res.ok) throw new Error(`Messages error: ${res.status}`)
  return res.json() as Promise<
    Array<{ id: number; type: string; content: string; read: boolean; createdAt: string }>
  >
}

// ── S2: 상태 머신 엔드포인트 ─────────────────────────────────────────────────

export async function pauseGameForCoach(
  gameId: string,
  reasonType: string,
  interventionScore: number,
  scoreDrop: number,
) {
  const res = await fetch(`${GAME_SERVER}/api/games/${gameId}/pause`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reasonType, interventionScore, scoreDrop }),
  })
  if (!res.ok) throw new Error(`Pause error: ${res.status}`)
  return res.json()
}

export async function resumeGame(gameId: string) {
  const res = await fetch(`${GAME_SERVER}/api/games/${gameId}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  if (!res.ok) throw new Error(`Resume error: ${res.status}`)
  return res.json()
}

export async function takebackMove(gameId: string) {
  const res = await fetch(`${GAME_SERVER}/api/games/${gameId}/takeback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  if (!res.ok) throw new Error(`Takeback error: ${res.status}`)
  return res.json() as Promise<{ newMoveCount: number; retractedMoveNumber: number }>
}

// ── S3: 코치 에이전트 ─────────────────────────────────────────────────────────

export interface VariationMoveOut {
  row: number
  col: number
  color: string
  label: string
}

export interface HintStepOut {
  step: number
  label: string
  text: string
}

export interface CoachPushResult {
  utterance: string
  verified: boolean
  verification_error: string
  variation: VariationMoveOut[]
  hints: HintStepOut[]
  cost: Record<string, number>
  llm_model: string
  latency_ms: number
}

export async function fetchCoachPush(payload: {
  game_id: string
  board_state: BoardState
  reason_type: string
  score_drop: number
  move_number: number
  color_that_moved: 'B' | 'W'
  best_move_korean?: string
}): Promise<CoachPushResult> {
  const res = await fetch(`${AI_SERVICE}/api/coach/push`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Coach push error: ${res.status}`)
  return res.json()
}

export interface ConversationTurn {
  role: 'user' | 'assistant'
  text: string
  move_number: number
}

export async function fetchCoachQuestion(payload: {
  game_id: string
  board_state: BoardState
  move_number: number
  question_text: string
  color_that_moved: 'B' | 'W'
  move_history?: GtpMove[]
  conversation_history?: ConversationTurn[]
}): Promise<{ question_type: string; answer: string; variation: VariationMoveOut[]; cost: Record<string, number>; llm_model: string; latency_ms: number }> {
  const res = await fetch(`${AI_SERVICE}/api/coach/question`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Coach question error: ${res.status}`)
  return res.json()
}

// ── Coach Answer 피드백 ───────────────────────────────────────────────────────

export interface SaveCoachAnswerPayload {
  kind: 'push' | 'reply'
  moveNumber: number
  questionText?: string
  answerText: string
  reasonType?: string | null
  verified?: boolean
  analysisSnapshot?: Record<string, unknown>
  llmModel?: string
  latencyMs?: number
}

export async function saveCoachAnswer(
  gameId: string,
  payload: SaveCoachAnswerPayload,
): Promise<{ id: number }> {
  const res = await fetch(`${GAME_SERVER}/api/games/${gameId}/coach-answers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`saveCoachAnswer error: ${res.status}`)
  return res.json()
}

export async function submitFeedback(
  answerId: number,
  rating: 'up' | 'down',
  feedbackReason?: string,
): Promise<void> {
  const res = await fetch(`${GAME_SERVER}/api/coach-answers/${answerId}/feedback`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating, feedbackReason }),
  })
  if (!res.ok) throw new Error(`submitFeedback error: ${res.status}`)
}

// ── User Games ───────────────────────────────────────────────────────────────

export interface GameSummary {
  id: string
  status: string
  mode: string
  boardSize: number
  komi: number
  moveCount: number
  result: string | null
  startedAt: string | null
  endedAt: string | null
  createdAt: string
}

export async function fetchMyGames(): Promise<GameSummary[]> {
  const res = await fetch(`${GAME_SERVER}/api/games/my`, {
    headers: await authHeader(),
  })
  if (!res.ok) throw new Error(`Fetch games error: ${res.status}`)
  return res.json()
}

export function sgfDownloadUrl(gameId: string): string {
  return `${GAME_SERVER}/api/games/${gameId}/sgf`
}

export async function submitScore(
  gameId: string,
  blackScore: number,
  whiteScore: number,
  method = 'territory',
) {
  const res = await fetch(`${GAME_SERVER}/api/games/${gameId}/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ method, blackScore, whiteScore }),
  })
  if (!res.ok) throw new Error(`Score error: ${res.status}`)
  return res.json() as Promise<{ result: string; blackScore: number; whiteScore: number }>
}
