'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useAuthStore } from '@/store/authStore'
import { GoBoard } from '@/components/GoBoard'
import { BoardOverlay } from '@/components/BoardOverlay'
import { TerritoryOverlay } from '@/components/TerritoryOverlay'
import { CoachPanel } from '@/components/CoachPanel'
import { GameHeader } from '@/components/GameHeader'
import { WinrateBar } from '@/components/WinrateBar'
import { GameResultDialog } from '@/components/GameResultDialog'
import { useGameStore } from '@/store/gameStore'
import type { GameMode, StoneColor } from '@/store/gameStore'
import { useStompGame } from '@/hooks/useStompGame'
import {
  createGame,
  fetchAiMove,
  logMove,
  checkIntervention,
  fetchCoachPush,
  fetchCoachQuestion,
  fetchDraft,
  moveHistoryToGtp,
  postUserQuestion,
  getGameMessages,
  pauseGameForCoach,
  resumeGame,
  takebackMove,
  submitScore,
  saveCoachAnswer,
  submitFeedback,
} from '@/lib/api'
import type { ConversationTurn } from '@/lib/api'
import { replayBoard } from '@/lib/boardReplay'
import { CIRCLED } from '@/lib/coordHighlight'
import type { CoordMarker } from '@/lib/coordHighlight'
import type { VariationMove } from '@/store/gameStore'

const GTP_COLS_STR = 'ABCDEFGHJKLMNOPQRST'
const KR_COLS_STR = '가나다라마바사아자차카타파하거너더러머'

function rowColToGtp(row: number, col: number): string {
  return GTP_COLS_STR[col] + (19 - row)
}

function rowColToKorean(row: number, col: number): string {
  return KR_COLS_STR[col] + (19 - row)
}

export default function GamePage() {
  const store = useGameStore()
  const { user } = useAuthStore()
  const [status, setStatus] = useState<'idle' | 'playing' | 'finished'>('idle')
  const [rankSelecting, setRankSelecting] = useState(false)
  const [questionInput, setQuestionInput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isCoachThinking, setIsCoachThinking] = useState(false)
  const prevScoreRef = useRef<number>(0)
  const prevWinrateRef = useRef<number>(0.5)
  const komiRef = useRef(6.5)

  useStompGame(store.gameId)

  useEffect(() => {
    if (store.gamePhase === 'FINISHED' && status !== 'finished') {
      setStatus('finished')
    }
  }, [store.gamePhase])

  async function startGame(mode: GameMode, aiRank?: string) {
    store.setMode(mode)
    store.setCoachEnabled(mode === 'AI_VS_HUMAN')
    try {
      const game = await createGame(19, 6.5, mode, aiRank)
      store.resetGame()
      store.setGameId(game.id)
      store.setMode(mode)
      if (aiRank) store.setAiRank(aiRank)
      komiRef.current = 6.5
      prevScoreRef.current = 0
      prevWinrateRef.current = 0.5
      setStatus('playing')
      setError(null)
    } catch {
      setError('게임 서버에 연결할 수 없습니다. 로컬 모드로 진행합니다.')
      store.resetGame()
      store.setGameId('local-' + Date.now())
      store.setMode(mode)
      if (aiRank) store.setAiRank(aiRank)
      komiRef.current = 6.5
      prevScoreRef.current = 0
      prevWinrateRef.current = 0.5
      setStatus('playing')
    }
  }

  async function handleScoringRequest() {
    store.enterScoringMode()
    await handleScoringConfirm()
  }

  async function handleScoringConfirm() {
    const { gameId, territoryMap } = useGameStore.getState()
    if (!territoryMap) return
    const blackScore = territoryMap.black.length
    const whiteScore = territoryMap.white.length + komiRef.current
    const resultStr =
      blackScore > whiteScore
        ? `B+${(blackScore - whiteScore).toFixed(1)}`
        : `W+${(whiteScore - blackScore).toFixed(1)}`

    if (gameId && !gameId.startsWith('local-')) {
      try {
        const res = await submitScore(gameId, blackScore, whiteScore)
        store.setGameResult({ result: res.result, blackScore, whiteScore })
      } catch {
        store.setGameResult({ result: resultStr, blackScore, whiteScore })
      }
    } else {
      store.setGameResult({ result: resultStr, blackScore, whiteScore })
    }
    setStatus('finished')
  }

  function handleScoringReject() {
    const { scoringRejectCount } = useGameStore.getState()
    if (scoringRejectCount >= 3) {
      handleScoringConfirm()
    } else {
      store.incrementScoringReject()
      store.exitScoringMode()
    }
  }

  function handleReview() {
    store.enterReviewMode()
    setStatus('playing')
  }

  function handleNewGame() {
    setStatus('idle')
    setRankSelecting(false)
    store.resetGame()
  }

  /** 색 공통: 수를 둔 뒤 KataGo 분석 + 자동 개입 체크 + 사범 발화 생성 */
  async function runPostMoveAnalysis(colorThatMoved: StoneColor) {
    const { gameId, board, moveCount, interventionCount, lastInterventionMove, moveHistory, aiRank } =
      useGameStore.getState()

    // 다음 수 평가용으로 KataGo에 다음 색의 수를 조회 (실제 착수에는 사용 안 함; 분석값만 활용)
    const nextColor: 'B' | 'W' = colorThatMoved === 1 ? 'W' : 'B'
    const aiMove = await fetchAiMove(
      gameId ?? 'local', board, moveCount + 1, nextColor, moveHistoryToGtp(moveHistory), aiRank ?? undefined,
    )

    // KataGo 값은 nextColor 시점이므로 colorThatMoved 시점으로 환산
    const movedScoreLead = -aiMove.score_lead
    const movedWinrate = 1 - aiMove.winrate

    // 화면 표시는 흑 기준으로 고정
    const blackScoreLead = colorThatMoved === 1 ? movedScoreLead : aiMove.score_lead
    const blackWinrate = colorThatMoved === 1 ? movedWinrate : aiMove.winrate
    store.setAnalysis(Math.max(0.05, Math.min(0.95, blackWinrate)), blackScoreLead)

    // ref는 항상 흑 시점으로 저장 → 착수자가 흑이면 그대로, 백이면 부호 반전
    const prevBlackScore = prevScoreRef.current
    const prevBlackWinrate = prevWinrateRef.current
    const scoreBefore = colorThatMoved === 1 ? prevBlackScore : -prevBlackScore
    const winrateBefore = colorThatMoved === 1 ? prevBlackWinrate : (1 - prevBlackWinrate)

    const lastMove = moveHistory[moveHistory.length - 1]
    const ivCheck = await checkIntervention({
      game_id: gameId ?? 'local',
      move_number: moveCount,
      score_before: scoreBefore,
      score_after: movedScoreLead,
      winrate_before: winrateBefore,
      winrate_after: movedWinrate,
      score_stdev: aiMove.score_stdev,
      interventions_so_far: interventionCount,
      last_intervention_move: lastInterventionMove,
      board_state: board,
      played_row: lastMove?.row,
      played_col: lastMove?.col,
      color_that_moved: colorThatMoved === 1 ? 'B' : 'W',
    }).catch(() => ({ triggered: false, reason_type: null, score_drop: 0, score: 0 }))

    prevScoreRef.current = blackScoreLead
    prevWinrateRef.current = blackWinrate

    const { coachEnabled } = useGameStore.getState()
    if (ivCheck.triggered && ivCheck.reason_type && coachEnabled) {
      const pendingPayload = {
        game_id: gameId ?? 'local',
        board_state: board,
        reason_type: ivCheck.reason_type,
        score_drop: ivCheck.score_drop,
        move_number: moveCount,
        color_that_moved: (colorThatMoved === 1 ? 'B' : 'W') as 'B' | 'W',
        move_history: moveHistoryToGtp(moveHistory),
      }

      // draft 말풍선 즉시 표시 — LLM은 "왜?" 클릭 시 호출
      const draftResult = await fetchDraft(pendingPayload).catch(() => null)
      if (draftResult) {
        store.addCoachMessage({
          id: crypto.randomUUID(),
          text: draftResult.draft_text,
          type: 'draft',
          createdAt: new Date(),
          pendingCoachPayload: pendingPayload,
        })
        // 나쁜 수 위치에 X 마커 표시
        const badRecord = useGameStore.getState().moveHistory.find(
          (m) => m.moveNumber === pendingPayload.move_number,
        )
        if (badRecord) store.setBadMoveMarker({ row: badRecord.row, col: badRecord.col })
        store.incrementIntervention(moveCount)

        // PvP: 자동 개입은 "방금 둔 사람" 전용으로 패널을 연다
        if (useGameStore.getState().mode === 'HUMAN_VS_HUMAN_LOCAL') {
          store.openQuestionPanel(colorThatMoved)
        }
      }
    }

    return { aiMove, blackWinrate, blackScoreLead }
  }

  async function handlePlace(row: number, col: number) {
    // useGameStore.getState()로 최신 상태를 읽어 stale closure 방지
    const { mode, isAiThinking, currentPlayer, gamePhase } = useGameStore.getState()
    if (isAiThinking) return
    if (gamePhase === 'COACH_PAUSE' || gamePhase === 'ANSWERING' || gamePhase === 'SCORING') return

    // AI 모드: 흑만 사람이 둔다
    if (mode === 'AI_VS_HUMAN' && currentPlayer !== 1) return

    const placedColor: StoneColor = currentPlayer
    const placed = store.placeStone(row, col)
    if (!placed) return

    store.clearCoachVariation()
    store.setPinnedCell(null)

    const { gameId } = useGameStore.getState()
    if (gameId && !gameId.startsWith('local-')) {
      logMove(gameId, placedColor === 1 ? 'BLACK' : 'WHITE', row, col, 'HUMAN').catch(() => {})
    }

    if (mode === 'HUMAN_VS_HUMAN_LOCAL') {
      // PvP: AI 응수 없음. 둔 색에 대해서만 분석/개입 체크.
      // 분석이 실패해도 승률바가 영원히 로딩 상태로 남지 않도록 복구한다.
      await runPostMoveAnalysis(placedColor).catch(() => {
        useGameStore.setState({ winrateLoading: false })
      })
      return
    }

    // AI 모드: 기존 흐름 (백은 AI가 응수)
    store.setAiThinking(true)
    try {
      const result = await runPostMoveAnalysis(placedColor)
      if (!result.aiMove.is_pass) {
        store.placeAiStone(result.aiMove.row, result.aiMove.col)
        if (gameId && !gameId.startsWith('local-')) {
          logMove(gameId, 'WHITE', result.aiMove.row, result.aiMove.col, 'AI').catch(() => {})
        }
      } else {
        store.setAiThinking(false)
      }
    } catch {
      store.setAiThinking(false)
      useGameStore.setState({ winrateLoading: false })
    }
  }

  async function handlePass() {
    const { mode, isAiThinking, currentPlayer, gamePhase } = useGameStore.getState()
    if (isAiThinking) return
    if (gamePhase === 'COACH_PAUSE' || gamePhase === 'ANSWERING') return
    if (mode === 'AI_VS_HUMAN' && currentPlayer !== 1) return

    const passedColor: StoneColor = currentPlayer
    store.passTurn()
    store.clearCoachVariation()

    const { gameId, board, moveCount, moveHistory } = useGameStore.getState()

    if (gameId && !gameId.startsWith('local-')) {
      logMove(gameId, passedColor === 1 ? 'BLACK' : 'WHITE', null, null, 'HUMAN').catch(() => {})
    }

    if (mode === 'HUMAN_VS_HUMAN_LOCAL') return

    store.setAiThinking(true)
    try {
      const { aiRank } = useGameStore.getState()
      const aiMove = await fetchAiMove(
        gameId ?? 'local', board, moveCount + 1, 'W', moveHistoryToGtp(moveHistory), aiRank ?? undefined,
      )
      if (!aiMove.is_pass) {
        store.placeAiStone(aiMove.row, aiMove.col)
        if (gameId && !gameId.startsWith('local-')) {
          logMove(gameId, 'WHITE', aiMove.row, aiMove.col, 'AI').catch(() => {})
        }
      } else {
        store.setAiThinking(false)
      }
    } catch {
      store.setAiThinking(false)
    }
  }

  async function handleTakeback() {
    const { gameId } = store
    if (gameId && !gameId.startsWith('local-')) {
      await takebackMove(gameId).catch(() => {})
    }
    store.takebackLastMove()
    store.clearCoachVariation()
  }

  function buildConversationHistory(
    msgs: import('@/store/gameStore').CoachMessage[],
    currentMoveNumber: number,
  ): ConversationTurn[] {
    // draft 제외, question/push/reply 만 포함. 최근 10턴(유저+AI 각 10개 = 20개) 으로 자름.
    const relevant = msgs.filter((m) => m.type === 'question' || m.type === 'push' || m.type === 'reply')
    return relevant.slice(-20).map((m) => ({
      role: m.type === 'question' ? 'user' : 'assistant',
      text: m.text,
      move_number: m.moveNumber ?? currentMoveNumber,
    }))
  }

  async function sendQuestion(overrideText?: string) {
    const text = overrideText ?? questionInput
    if (!text.trim()) return
    const { gameId, board, moveCount, currentPlayer, coachMessages } = store
    // "방금 둔 색"은 수순 상 currentPlayer(다음 둘 색)의 반대. 모드 무관.
    const colorMoved = currentPlayer === 1 ? 'W' : 'B'

    // 유저 질문을 먼저 스토어에 저장해 채팅 UI에 즉시 표시하고 이후 히스토리에도 포함
    store.addCoachMessage({
      id: crypto.randomUUID(),
      text,
      type: 'question',
      createdAt: new Date(),
      moveNumber: moveCount,
    })
    if (!overrideText) setQuestionInput('')

    const conversationHistory = buildConversationHistory(coachMessages, moveCount)

    setIsCoachThinking(true)
    const coachReply = await fetchCoachQuestion({
      game_id: gameId ?? 'local',
      board_state: board,
      move_number: moveCount,
      question_text: text,
      color_that_moved: colorMoved,
      move_history: moveHistoryToGtp(store.moveHistory),
      conversation_history: conversationHistory,
    }).catch(() => null).finally(() => setIsCoachThinking(false))

    if (coachReply) {
      const msgId = crypto.randomUUID()
      store.addCoachMessage({
        id: msgId,
        text: coachReply.answer,
        type: 'reply',
        createdAt: new Date(),
        moveNumber: moveCount,
      })
      if (coachReply.variation.length > 0) {
        store.setCoachVariation(coachReply.variation)
      }
      if (gameId && !gameId.startsWith('local-')) {
        saveCoachAnswer(gameId, {
          kind: 'reply',
          moveNumber: store.moveCount,
          questionText: text,
          answerText: coachReply.answer,
          llmModel: coachReply.llm_model,
          latencyMs: coachReply.latency_ms,
        }).then(({ id }) => store.updateCoachMessage(msgId, { answerId: id })).catch(() => {})
      }
    } else {
      if (gameId && !gameId.startsWith('local-')) {
        await postUserQuestion(gameId, text).catch(() => {})
      }
    }
  }

  async function handleAskPinned() {
    const { pinnedCell } = useGameStore.getState()
    if (!pinnedCell) return
    store.setPinnedCell(null)
    await sendQuestion(`여기에 두면 좋은 수인가요? (${rowColToGtp(pinnedCell.row, pinnedCell.col)})`)
  }

  async function handleWhyAsk() {
    const { gameId, board, moveCount, currentPlayer, coachMessages, moveHistory } = store

    // draft 메시지가 있으면 LLM 분석을 실행하고 push로 업그레이드
    const lastDraft = [...coachMessages].reverse().find((m) => m.type === 'draft' && m.pendingCoachPayload)
    if (lastDraft?.pendingCoachPayload) {
      store.setGamePhase('COACH_PAUSE')
      if (gameId && !gameId.startsWith('local-')) {
        await pauseGameForCoach(
          gameId,
          lastDraft.pendingCoachPayload.reason_type,
          0,
          lastDraft.pendingCoachPayload.score_drop,
        ).catch(() => {})
      }

      setIsCoachThinking(true)
      const coachResult = await fetchCoachPush(lastDraft.pendingCoachPayload).catch(() => null)
      setIsCoachThinking(false)
      if (coachResult) {
        const msgId = crypto.randomUUID()
        store.updateCoachMessage(lastDraft.id, {
          type: 'push',
          text: coachResult.utterance,
          verified: coachResult.verified,
          verificationError: coachResult.verification_error,
          pendingCoachPayload: undefined,
        })
        if (gameId && !gameId.startsWith('local-')) {
          saveCoachAnswer(gameId, {
            kind: 'push',
            moveNumber: lastDraft.pendingCoachPayload.move_number,
            answerText: coachResult.utterance,
            reasonType: lastDraft.pendingCoachPayload.reason_type,
            verified: coachResult.verified,
            analysisSnapshot: {
              winrate: store.blackWinrate,
              scoreLead: store.scoreLead,
              scoreStdev: 0,
              interventionScore: 0,
              scoreDrop: lastDraft.pendingCoachPayload.score_drop,
            },
            llmModel: coachResult.llm_model,
            latencyMs: coachResult.latency_ms,
          }).then(({ id }) => store.updateCoachMessage(lastDraft.id, { answerId: id })).catch(() => {})
        }
        if (coachResult.variation.length > 0) store.setCoachVariation(coachResult.variation)
        if (coachResult.hints.length > 0) store.setActiveHints(coachResult.hints)
        void msgId
      }

      if (gameId && !gameId.startsWith('local-')) {
        await resumeGame(gameId).catch(() => {})
      }
      store.setGamePhase('PLAYING')
      return
    }

    // draft 없으면 기존 push 메시지 기반 "왜?" Q&A
    const lastPush = [...coachMessages].reverse().find((m) => m.type === 'push')
    if (!lastPush) return

    const colorMoved = currentPlayer === 1 ? 'W' : 'B'
    const questionText = `방금 수가 왜 나쁜가요? 사범이 말씀하신 내용: "${lastPush.text}"`

    store.addCoachMessage({
      id: crypto.randomUUID(),
      text: questionText,
      type: 'question',
      createdAt: new Date(),
      moveNumber: moveCount,
    })

    setIsCoachThinking(true)
    const coachReply = await fetchCoachQuestion({
      game_id: gameId ?? 'local',
      board_state: board,
      move_number: moveCount,
      question_text: questionText,
      color_that_moved: colorMoved,
      move_history: moveHistoryToGtp(moveHistory),
      conversation_history: buildConversationHistory(coachMessages, moveCount),
    }).catch(() => null)
    setIsCoachThinking(false)

    if (coachReply) {
      store.addCoachMessage({
        id: crypto.randomUUID(),
        text: coachReply.answer,
        type: 'reply',
        createdAt: new Date(),
        moveNumber: moveCount,
      })
    }
  }

  function handleFeedback(messageId: string, rating: 'up' | 'down', reason?: string) {
    const msg = store.coachMessages.find((m) => m.id === messageId)
    if (!msg?.answerId) return
    store.updateCoachMessage(messageId, { rating, feedbackReason: reason })
    submitFeedback(msg.answerId, rating, reason).catch(() => {})
  }

  function handleSequenceClick(moves: CoordMarker[]) {
    const { currentPlayer } = useGameStore.getState()
    const firstColor: 'B' | 'W' = currentPlayer === 1 ? 'B' : 'W'
    const variation: VariationMove[] = moves.map((m, i) => ({
      row: m.row,
      col: m.col,
      color: i % 2 === 0 ? firstColor : (firstColor === 'B' ? 'W' : 'B'),
      label: CIRCLED[i] ?? String(i + 1),
    }))
    store.setCoachVariation(variation)
  }

  useEffect(() => {
    const { gameId } = store
    if (!gameId || gameId.startsWith('local-') || status !== 'playing') return
    const id = setInterval(async () => {
      const msgs = await getGameMessages(gameId).catch(() => [])
      for (const m of msgs) {
        const already = store.coachMessages.some((cm) => cm.id === String(m.id))
        if (!already && m.type === 'COACH_PUSH') {
          store.addCoachMessage({
            id: String(m.id),
            text: m.content,
            type: 'push',
            createdAt: new Date(m.createdAt),
          })
        }
      }
    }, 5000)
    return () => clearInterval(id)
  }, [store.gameId, status])

  const isCoachActive = store.gamePhase === 'COACH_PAUSE' || store.gamePhase === 'ANSWERING'
  const isReview = store.gamePhase === 'REVIEW'
  const activeMoves = store.moveHistory.filter((m) => !m.retracted)
  const displayBoard = isReview ? replayBoard(store.moveHistory, store.reviewStep) : store.board
  const displayHistory = isReview ? activeMoves.slice(0, store.reviewStep) : store.moveHistory
  const isPvp = store.mode === 'HUMAN_VS_HUMAN_LOCAL'

  // A안: PvP에서 패널이 열려있으면 그 색의 턴에만 보여준다. 복기는 양쪽 공개.
  const pvpVisibility: 'hidden' | 'open-for-black' | 'open-for-white' | 'review' | undefined =
    isReview
      ? 'review'
      : isPvp
      ? store.questionPanelOpenFor === null
        ? 'hidden'
        : store.questionPanelOpenFor === 1
        ? 'open-for-black'
        : 'open-for-white'
      : undefined

  const boardDisabled =
    store.isAiThinking ||
    isCoachActive ||
    store.gamePhase === 'SCORING' ||
    isReview ||
    (store.mode === 'AI_VS_HUMAN' && store.currentPlayer !== 1)

  return (
    <main className="flex flex-col items-center p-4 gap-4 min-h-screen bg-stone-50">
      <div className="w-full max-w-4xl flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">수담</h1>
        {user ? (
          <Link href="/dashboard" className="text-sm text-amber-600 hover:underline font-medium">
            {user.nickname || user.email} · 내 기록
          </Link>
        ) : (
          <Link href="/login" className="text-sm text-gray-500 hover:text-gray-800 transition">
            로그인
          </Link>
        )}
      </div>

      {status === 'idle' && !rankSelecting && (
        <div className="flex flex-col gap-3 items-center mt-6">
          <button
            onClick={() => setRankSelecting(true)}
            className="px-8 py-4 bg-amber-700 text-white rounded-xl text-lg font-semibold hover:bg-amber-800 transition shadow"
          >
            AI와 대국
          </button>
          <button
            onClick={() => startGame('HUMAN_VS_HUMAN_LOCAL')}
            className="px-8 py-4 bg-emerald-700 text-white rounded-xl text-lg font-semibold hover:bg-emerald-800 transition shadow"
          >
            둘이서 대국 (한 화면)
          </button>
          <p className="text-xs text-gray-500 mt-1 text-center max-w-xs">
            "둘이서 대국"은 한 디바이스에서 번갈아 두는 핫시트 모드입니다.<br/>
            AI 사범이 결정적 순간에만 조언하며, 사범 패널은 현재 턴 플레이어만 열람할 수 있습니다.
          </p>
        </div>
      )}

      {status === 'idle' && rankSelecting && (
        <div className="flex flex-col gap-4 items-center mt-6">
          <p className="text-base font-semibold text-gray-700">AI 상대 급수를 선택하세요</p>
          <div className="flex gap-3">
            {([
              { label: '10급', value: 'preaz_10k' },
              { label: '5급',  value: 'preaz_5k' },
              { label: '초단', value: 'preaz_1d' },
              { label: '5단',  value: 'preaz_5d' },
            ] as const).map(({ label, value }) => (
              <button
                key={value}
                onClick={() => { setRankSelecting(false); startGame('AI_VS_HUMAN', value) }}
                className="px-6 py-3 bg-amber-700 text-white rounded-xl text-base font-semibold hover:bg-amber-800 transition shadow"
              >
                {label}
              </button>
            ))}
          </div>
          <button
            onClick={() => setRankSelecting(false)}
            className="text-sm text-gray-400 hover:text-gray-600 transition"
          >
            뒤로
          </button>
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {status === 'playing' && (
        <div className="flex flex-col items-center gap-3 w-full max-w-4xl">
          <GameHeader
            moveCount={store.moveCount}
            blackTimeMs={store.blackTimeMs}
            whiteTimeMs={store.whiteTimeMs}
            currentPlayer={store.currentPlayer}
            isAiThinking={store.isAiThinking}
            gamePhase={store.gamePhase}
            mode={store.mode}
          />
          <WinrateBar
            blackWinrate={store.blackWinrate}
            scoreLead={store.scoreLead}
            loading={store.winrateLoading}
          />

          <div className="flex gap-6 items-start flex-wrap justify-center">
            <div className="flex flex-col items-center gap-2">
              <GoBoard
                board={displayBoard}
                moveHistory={displayHistory}
                currentPlayer={store.currentPlayer}
                onPlace={handlePlace}
                disabled={boardDisabled}
                pinMode={isCoachActive}
                onPin={(r, c) => store.setPinnedCell({ row: r, col: c })}
                pinnedCell={store.pinnedCell}

                bgOverlay={
                  store.gamePhase === 'SCORING' && store.territoryMap ? (
                    <TerritoryOverlay
                      black={store.territoryMap.black}
                      white={store.territoryMap.white}
                    />
                  ) : undefined
                }
                overlay={
                  store.coachVariation.length > 0 || store.badMoveMarker ? (
                    <BoardOverlay
                      moves={store.coachVariation}
                      visibleCount={store.variationStep}
                      hidden={store.variationHidden}
                      badMoves={store.badMoveMarker ? [store.badMoveMarker] : undefined}
                    />
                  ) : undefined
                }
              />
              <div className="flex gap-2 mt-1">
                <button
                  onClick={handleTakeback}
                  disabled={store.moveCount === 0 || store.isAiThinking}
                  className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-40 transition"
                >
                  고쳐 두기
                </button>
                <button
                  onClick={handlePass}
                  disabled={
                    store.isAiThinking ||
                    isCoachActive ||
                    (store.mode === 'AI_VS_HUMAN' && store.currentPlayer !== 1)
                  }
                  className="px-3 py-1 text-xs bg-amber-100 text-amber-800 rounded hover:bg-amber-200 disabled:opacity-40 transition"
                >
                  패스
                </button>
                {store.gamePhase === 'SCORING' ? (
                  <>
                    <button
                      onClick={handleScoringConfirm}
                      className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                    >
                      결과 동의
                    </button>
                    <button
                      onClick={handleScoringReject}
                      className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
                    >
                      거절{store.scoringRejectCount > 0 ? ` (${store.scoringRejectCount}/3)` : ''}
                    </button>
                  </>
                ) : store.gamePhase === 'REVIEW' ? null : (
                  <button
                    onClick={handleScoringRequest}
                    disabled={store.isAiThinking || isCoachActive}
                    className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-40 transition"
                  >
                    계가신청
                  </button>
                )}
              </div>
              {store.gamePhase === 'SCORING' && store.territoryMap && (
                <div className="flex gap-4 text-sm font-medium">
                  <span className="text-blue-700">
                    흑 {store.territoryMap.black.length}집
                  </span>
                  <span className="text-orange-600">
                    백 {store.territoryMap.white.length}집
                    {' '}(+{komiRef.current} = {(store.territoryMap.white.length + komiRef.current).toFixed(1)})
                  </span>
                </div>
              )}

              {isReview && (
                <div className="flex flex-col items-center gap-2 w-full">
                  <p className="text-xs text-gray-500">
                    {store.reviewStep} / {activeMoves.length} 수
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => store.setReviewStep(0)}
                      disabled={store.reviewStep === 0}
                      className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-40 transition"
                    >
                      ◀◀
                    </button>
                    <button
                      onClick={() => store.setReviewStep(Math.max(0, store.reviewStep - 1))}
                      disabled={store.reviewStep === 0}
                      className="px-3 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-40 transition"
                    >
                      ◀
                    </button>
                    <button
                      onClick={() => store.setReviewStep(Math.min(activeMoves.length, store.reviewStep + 1))}
                      disabled={store.reviewStep >= activeMoves.length}
                      className="px-3 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-40 transition"
                    >
                      ▶
                    </button>
                    <button
                      onClick={() => store.setReviewStep(activeMoves.length)}
                      disabled={store.reviewStep >= activeMoves.length}
                      className="px-2 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-40 transition"
                    >
                      ▶▶
                    </button>
                  </div>
                  <button
                    onClick={handleNewGame}
                    className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
                  >
                    새 대국
                  </button>
                </div>
              )}
            </div>

            <CoachPanel
              messages={store.coachMessages}
              isCoachThinking={isCoachThinking}
              variation={store.coachVariation}
              variationStep={store.variationStep}
              variationHidden={store.variationHidden}
              hints={store.activeHints}
              currentHintStep={store.currentHintStep}
              questionInput={questionInput}
              isCoachActive={isCoachActive}
              onVariationStep={store.setVariationStep}
              onCloseVariation={store.clearCoachVariation}
              onVariationHideToggle={() => store.setVariationHidden(!store.variationHidden)}
              onRevealHint={store.revealNextHint}
              onQuestionChange={setQuestionInput}
              onSendQuestion={() => sendQuestion()}
              onPresetQuestion={(text) => sendQuestion(text)}
              onWhyAsk={handleWhyAsk}
              onSequenceClick={handleSequenceClick}
              pinnedCoordLabel={store.pinnedCell ? rowColToKorean(store.pinnedCell.row, store.pinnedCell.col) : null}
              onAskPinned={handleAskPinned}
              onClearPin={() => store.setPinnedCell(null)}
              pvpVisibility={pvpVisibility}
              onOpenPanel={() => store.openQuestionPanel(store.currentPlayer)}
              onClosePanel={() => store.closeQuestionPanel()}
              onFeedback={handleFeedback}
              coachEnabled={store.coachEnabled}
              onToggleCoach={store.setCoachEnabled}
            />
          </div>
        </div>
      )}

      {store.gameResult && status === 'finished' && (
        <GameResultDialog
          result={store.gameResult}
          moveHistory={store.moveHistory}
          komi={komiRef.current}
          onClose={handleNewGame}
          onReview={handleReview}
        />
      )}
    </main>
  )
}
