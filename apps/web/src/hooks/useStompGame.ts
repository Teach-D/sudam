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
        const row = payload.row as number
        const col = payload.col as number
        store.placeAiStone(row, col)
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
