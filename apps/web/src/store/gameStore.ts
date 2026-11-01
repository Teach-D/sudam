'use client'

import { create } from 'zustand'
import { computeTerritory, TerritoryResult } from '@/lib/territory'

export type StoneColor = 1 | 2  // 1=black, 2=white
export type BoardState = number[][]
export type GamePhase = 'PLAYING' | 'COACH_PAUSE' | 'ANSWERING' | 'FINISHED' | 'SCORING' | 'REVIEW'
export type GameMode = 'AI_VS_HUMAN' | 'HUMAN_VS_HUMAN_LOCAL'

export interface MoveRecord {
  row: number
  col: number
  color: StoneColor
  moveNumber: number
  retracted?: boolean
}

export interface PendingCoachPayload {
  game_id: string
  board_state: number[][]
  reason_type: string
  score_drop: number
  move_number: number
  color_that_moved: 'B' | 'W'
}

export interface CoachMessage {
  id: string
  text: string
  type: 'push' | 'reply' | 'draft' | 'question'
  createdAt: Date
  moveNumber?: number
  verified?: boolean
  verificationError?: string
  answerId?: number
  rating?: 'up' | 'down'
  feedbackReason?: string
  pendingCoachPayload?: PendingCoachPayload
}

export interface VariationMove {
  row: number
  col: number
  color: string
  label: string
}

export interface HintStep {
  step: number
  label: string
  text: string
}

export interface GameResult {
  result: string      // "B+5.5" or "W+3.0"
  blackScore: number
  whiteScore: number
}

interface GameStore {
  gameId: string | null
  mode: GameMode
  aiRank: string | null
  board: BoardState
  currentPlayer: StoneColor
  moveHistory: MoveRecord[]
  moveCount: number
  isAiThinking: boolean
  coachMessages: CoachMessage[]
  interventionCount: number
  lastInterventionMove: number
  coachEnabled: boolean
  userQuestion: string
  // PvP: 질의자가 사범 패널을 연 상태. 다음 수가 놓이면 자동으로 닫혀서 상대 턴에 노출되지 않는다.
  questionPanelOpenFor: StoneColor | null

  // S2: 새 상태
  gamePhase: GamePhase
  blackWinrate: number    // 0.0–1.0
  scoreLead: number       // 양수 = 흑 우세
  // 수를 둔 뒤 새 KataGo 분석을 기다리는 동안 true. 이전 승률을 그대로 유지한 채
  // 로딩 UI만 표시해 50/50 중간 상태로 튀는 깜빡임을 방지한다.
  winrateLoading: boolean
  blackTimeMs: number
  whiteTimeMs: number
  gameResult: GameResult | null

  // S3: 코치 에이전트
  coachVariation: VariationMove[]
  variationStep: number         // 현재 보여줄 수순 단계 (0 = 전체)
  activeHints: HintStep[]
  currentHintStep: number       // 0 = 힌트 없음, 1~3 = 공개된 단계

  // 계가
  territoryMap: TerritoryResult | null
  scoringRejectCount: number

  // 복기
  reviewStep: number

  setGameId: (id: string) => void
  setMode: (mode: GameMode) => void
  setAiRank: (rank: string | null) => void
  openQuestionPanel: (color: StoneColor) => void
  closeQuestionPanel: () => void
  placeStone: (row: number, col: number) => boolean
  setAiThinking: (v: boolean) => void
  placeAiStone: (row: number, col: number) => void
  addCoachMessage: (msg: CoachMessage) => void
  updateCoachMessage: (id: string, patch: Partial<CoachMessage>) => void
  incrementIntervention: (moveNumber: number) => void
  setCoachEnabled: (v: boolean) => void
  setUserQuestion: (q: string) => void
  resetGame: () => void

  // S2 액션
  setGamePhase: (phase: GamePhase) => void
  setAnalysis: (winrate: number, scoreLead: number) => void
  setClockTimes: (blackMs: number, whiteMs: number) => void
  setGameResult: (result: GameResult) => void
  takebackLastMove: () => void
  passTurn: () => void

  // S3 액션
  setCoachVariation: (moves: VariationMove[]) => void
  setVariationStep: (step: number) => void
  setActiveHints: (hints: HintStep[]) => void
  revealNextHint: () => void
  clearCoachVariation: () => void

  // 계가 액션
  enterScoringMode: () => void
  exitScoringMode: () => void
  incrementScoringReject: () => void

  // 복기 액션
  setReviewStep: (step: number) => void
  enterReviewMode: () => void

  // 좌표 핀
  pinnedCell: { row: number; col: number } | null
  setPinnedCell: (cell: { row: number; col: number } | null) => void
}

const BOARD_SIZE = 19

function emptyBoard(): BoardState {
  return Array.from({ length: BOARD_SIZE }, () => new Array(BOARD_SIZE).fill(0))
}

function boardNeighbors(row: number, col: number): [number, number][] {
  const result: [number, number][] = []
  if (row > 0) result.push([row - 1, col])
  if (row < BOARD_SIZE - 1) result.push([row + 1, col])
  if (col > 0) result.push([row, col - 1])
  if (col < BOARD_SIZE - 1) result.push([row, col + 1])
  return result
}

function getGroup(board: BoardState, row: number, col: number): [number, number][] {
  const color = board[row][col]
  if (color === 0) return []
  const visited = new Set<string>()
  const stack: [number, number][] = [[row, col]]
  const group: [number, number][] = []
  while (stack.length > 0) {
    const [r, c] = stack.pop()!
    const key = `${r},${c}`
    if (visited.has(key)) continue
    visited.add(key)
    group.push([r, c])
    for (const [nr, nc] of boardNeighbors(r, c)) {
      if (board[nr][nc] === color && !visited.has(`${nr},${nc}`)) {
        stack.push([nr, nc])
      }
    }
  }
  return group
}

function hasLiberty(board: BoardState, group: [number, number][]): boolean {
  for (const [r, c] of group) {
    for (const [nr, nc] of boardNeighbors(r, c)) {
      if (board[nr][nc] === 0) return true
    }
  }
  return false
}

export const useGameStore = create<GameStore>((set, get) => ({
  gameId: null,
  mode: 'AI_VS_HUMAN',
  aiRank: null,
  board: emptyBoard(),
  currentPlayer: 1,
  moveHistory: [],
  moveCount: 0,
  isAiThinking: false,
  coachMessages: [],
  interventionCount: 0,
  lastInterventionMove: -20,
  coachEnabled: true,
  userQuestion: '',
  questionPanelOpenFor: null,
  gamePhase: 'PLAYING',
  blackWinrate: 0.5,
  scoreLead: 0,
  winrateLoading: false,
  blackTimeMs: 0,
  whiteTimeMs: 0,
  gameResult: null,
  scoringRejectCount: 0,
  reviewStep: 0,
  coachVariation: [],
  pinnedCell: null,
  variationStep: 0,
  activeHints: [],
  currentHintStep: 0,
  territoryMap: null,

  setGameId: (id) => set({ gameId: id }),
  setMode: (mode) => set({ mode }),
  setAiRank: (rank) => set({ aiRank: rank }),
  setCoachEnabled: (v) => set({ coachEnabled: v }),
  openQuestionPanel: (color) => set({ questionPanelOpenFor: color }),
  closeQuestionPanel: () => set({ questionPanelOpenFor: null }),

  placeStone: (row, col) => {
    const { board, currentPlayer, moveHistory, moveCount, gamePhase } = get()
    if (gamePhase === 'SCORING') return false
    if (board[row][col] !== 0) return false

    const newBoard = board.map((r) => [...r])
    newBoard[row][col] = currentPlayer
    const opponent = currentPlayer === 1 ? 2 : 1

    // 상대 그룹 중 활로가 0이 된 것을 따낸다
    for (const [nr, nc] of boardNeighbors(row, col)) {
      if (newBoard[nr][nc] === opponent) {
        const group = getGroup(newBoard, nr, nc)
        if (!hasLiberty(newBoard, group)) {
          for (const [gr, gc] of group) {
            newBoard[gr][gc] = 0
          }
        }
      }
    }

    // 자충: 따냄 후에도 착수한 그룹의 활로가 0이면 불법
    if (!hasLiberty(newBoard, getGroup(newBoard, row, col))) {
      return false
    }

    const record: MoveRecord = {
      row,
      col,
      color: currentPlayer,
      moveNumber: moveCount + 1,
    }

    set({
      board: newBoard,
      currentPlayer: currentPlayer === 1 ? 2 : 1,
      moveHistory: [...moveHistory, record],
      moveCount: moveCount + 1,
      // A안: 수가 놓이면 열려있던 질의 패널은 자동으로 닫혀 다음 플레이어에게 노출되지 않는다.
      questionPanelOpenFor: null,
      winrateLoading: true,
    })
    return true
  },

  setAiThinking: (v) => set({ isAiThinking: v }),

  placeAiStone: (row, col) => {
    const { board, moveHistory, moveCount } = get()
    // 이미 점유된 셀에 중복 착수 방지 (stale closure 경쟁 조건의 방어 레이어)
    if (board[row][col] !== 0) return
    const newBoard = board.map((r) => [...r])
    newBoard[row][col] = 2

    // 흑 그룹 중 활로가 0이 된 것을 따낸다
    for (const [nr, nc] of boardNeighbors(row, col)) {
      if (newBoard[nr][nc] === 1) {
        const group = getGroup(newBoard, nr, nc)
        if (!hasLiberty(newBoard, group)) {
          for (const [gr, gc] of group) {
            newBoard[gr][gc] = 0
          }
        }
      }
    }

    const record: MoveRecord = {
      row,
      col,
      color: 2,
      moveNumber: moveCount + 1,
    }

    set({
      board: newBoard,
      currentPlayer: 1,
      moveHistory: [...moveHistory, record],
      moveCount: moveCount + 1,
      isAiThinking: false,
      questionPanelOpenFor: null,
    })
  },

  addCoachMessage: (msg) =>
    set((s) => ({ coachMessages: [...s.coachMessages, msg] })),

  updateCoachMessage: (id, patch) =>
    set((s) => ({
      coachMessages: s.coachMessages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),

  incrementIntervention: (moveNumber) =>
    set((s) => ({
      interventionCount: s.interventionCount + 1,
      lastInterventionMove: moveNumber,
    })),

  setUserQuestion: (q) => set({ userQuestion: q }),

  setGamePhase: (phase) => set({ gamePhase: phase }),

  setAnalysis: (winrate, scoreLead) =>
    set({ blackWinrate: winrate, scoreLead, winrateLoading: false }),

  setClockTimes: (blackMs, whiteMs) => set({ blackTimeMs: blackMs, whiteTimeMs: whiteMs }),

  setGameResult: (result) => set({ gameResult: result, gamePhase: 'FINISHED' }),

  setCoachVariation: (moves) => set({ coachVariation: moves, variationStep: 0 }),
  setVariationStep: (step) => set({ variationStep: step }),
  setActiveHints: (hints) => set({ activeHints: hints, currentHintStep: 0 }),
  revealNextHint: () =>
    set((s) => ({
      currentHintStep: Math.min(s.currentHintStep + 1, s.activeHints.length),
    })),
  clearCoachVariation: () => set({ coachVariation: [], variationStep: 0 }),

  enterScoringMode: () => {
    const { board } = get()
    set({ territoryMap: computeTerritory(board), gamePhase: 'SCORING' })
  },

  exitScoringMode: () => set({ territoryMap: null, gamePhase: 'PLAYING' }),

  incrementScoringReject: () =>
    set((s) => ({ scoringRejectCount: s.scoringRejectCount + 1 })),

  setReviewStep: (step) => set({ reviewStep: step }),

  enterReviewMode: () => {
    const { moveHistory } = get()
    set({ gamePhase: 'REVIEW', reviewStep: moveHistory.filter((m) => !m.retracted).length })
  },

  setPinnedCell: (cell) => set({ pinnedCell: cell }),

  passTurn: () => {
    const { currentPlayer, moveCount } = get()
    set({
      currentPlayer: currentPlayer === 1 ? 2 : 1,
      moveCount: moveCount + 1,
    })
  },

  takebackLastMove: () => {
    const { board, moveHistory, moveCount, currentPlayer } = get()
    const lastActive = [...moveHistory].reverse().find((m) => !m.retracted)
    if (!lastActive) return

    // 보드에서 제거
    const newBoard = board.map((r) => [...r])
    newBoard[lastActive.row][lastActive.col] = 0

    const newHistory = moveHistory.map((m) =>
      m.moveNumber === lastActive.moveNumber ? { ...m, retracted: true } : m,
    )

    set({
      board: newBoard,
      currentPlayer: lastActive.color,  // 무른 돌 색이 다시 착수
      moveHistory: newHistory,
      moveCount: moveCount - 1,
    })
  },

  resetGame: () =>
    set((s) => ({
      gameId: null,
      mode: s.mode,  // 모드는 로비에서 설정하므로 리셋 중 보존
      board: emptyBoard(),
      currentPlayer: 1,
      moveHistory: [],
      moveCount: 0,
      isAiThinking: false,
      coachMessages: [],
      interventionCount: 0,
      lastInterventionMove: -20,
      coachEnabled: s.coachEnabled,
      userQuestion: '',
      questionPanelOpenFor: null,
      gamePhase: 'PLAYING',
      blackWinrate: 0.5,
      scoreLead: 0,
      winrateLoading: false,
      blackTimeMs: 0,
      whiteTimeMs: 0,
      gameResult: null,
      coachVariation: [],
      variationStep: 0,
      activeHints: [],
      currentHintStep: 0,
      territoryMap: null,
      scoringRejectCount: 0,
      reviewStep: 0,
      pinnedCell: null,
    })),
}))
