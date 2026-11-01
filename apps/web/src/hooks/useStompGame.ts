'use client'

import { useEffect, useRef } from 'react'
import { Client } from '@stomp/stompjs'
import SockJS from 'sockjs-client'
import { useGameStore } from '@/store/gameStore'

const GAME_SERVER = process.env.NEXT_PUBLIC_GAME_SERVER_URL ?? 'http://localhost:8080'

export function useStompGame(gameId: string | null) {
  const store = useGameStore()
  const clientRef = useRef<Client | null>(null)

  useEffect(() => {
    if (!gameId || gameId.startsWith('local-')) return

    const client = new Client({
      webSocketFactory: () => new SockJS(`${GAME_SERVER}/ws`),
      reconnectDelay: 3000,
      onConnect: () => {
        client.subscribe(`/topic/game/${gameId}`, (frame) => {
          try {
            const event = JSON.parse(frame.body) as { type: string; payload: Record<string, unknown> }
            handleEvent(event.type, event.payload)
          } catch {
            // ignore malformed frames
          }
        })
      },
    })

    client.activate()
    clientRef.current = client

    return () => {
      client.deactivate()
      clientRef.current = null
    }
  }, [gameId])

  function handleEvent(type: string, payload: Record<string, unknown>) {
    switch (type) {
      case 'move.ai': {
        // 프론트엔드가 AI 수를 직접 처리(handlePlace → placeAiStone)하므로
        // WebSocket 이벤트로 다시 처리하면 moveHistory/moveCount가 중복된다.
        // KataGo 분석값이 없는 이벤트에서 0.5로 fallback 하면 승률바가 50/50으로 튄다.
        // 값이 실제로 담겨있을 때만 반영한다.
        if (payload.winrate != null && payload.scoreLead != null) {
          store.setAnalysis(payload.winrate as number, payload.scoreLead as number)
        }
        break
      }
      case 'move.play': {
        if (payload.winrate != null && payload.scoreLead != null) {
          store.setAnalysis(payload.winrate as number, payload.scoreLead as number)
        }
        break
      }
      case 'coach.pause': {
        store.setGamePhase('COACH_PAUSE')
        const reasonType = payload.reasonType as string
        const scoreDrop = payload.scoreDrop as number
        if (reasonType) {
          store.addCoachMessage({
            id: crypto.randomUUID(),
            text: `[사범] ${reasonType} — 점수 손실: ${scoreDrop?.toFixed(1) ?? '?'}점`,
            type: 'push',
            createdAt: new Date(),
          })
        }
        break
      }
      case 'coach.resume':
        store.setGamePhase('PLAYING')
        break

      case 'move.retract': {
        store.takebackLastMove()
        break
      }
      case 'game.end': {
        store.setGameResult({
          result: payload.result as string,
          blackScore: payload.blackScore as number,
          whiteScore: payload.whiteScore as number,
        })
        break
      }
    }
  }

  return clientRef
}
