export interface CoordMarker {
  row: number
  col: number
  label: string
  coordText: string
}

export type TextSegment =
  | { type: 'text'; content: string }
  | { type: 'coord'; content: string; marker: CoordMarker }
  | { type: 'sequence'; content: string; moves: CoordMarker[] }

const KR_COLS = '가나다라마바사아자차카타파하거너더러머'
const COORD_RE = /[가나다라마바사아자차카타파하거너더러머](?:19|1[0-8]|[1-9])/g
export const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']

// 인접한 좌표 세그먼트가 → 또는 -> 로 연결된 경우 sequence로 묶는다
function mergeSequences(segments: TextSegment[]): TextSegment[] {
  const result: TextSegment[] = []
  let i = 0
  while (i < segments.length) {
    const seg = segments[i]
    if (seg.type !== 'coord') {
      result.push(seg)
      i++
      continue
    }

    const seqMoves: CoordMarker[] = [seg.marker]
    let seqContent = seg.content
    let j = i + 1

    while (j + 1 < segments.length) {
      const sep = segments[j]
      const next = segments[j + 1]
      if (sep.type !== 'text' || next.type !== 'coord') break
      // 좌표 뒤에 붙는 "(좌상 화점)" 같은 설명 괄호도 구분자로 허용
      if (!/^\s*(?:\([^)]*\))?\s*(?:→|->)\s*$/.test(sep.content)) break
      seqMoves.push(next.marker)
      seqContent += sep.content + next.content
      j += 2
    }

    if (seqMoves.length >= 2) {
      result.push({ type: 'sequence', content: seqContent, moves: seqMoves })
      i = j
    } else {
      result.push(seg)
      i++
    }
  }
  return result
}

export function splitWithCoords(text: string): TextSegment[] {
  const raw: TextSegment[] = []
  const markerMap = new Map<string, CoordMarker>()
  let count = 0
  let lastIndex = 0

  COORD_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = COORD_RE.exec(text)) !== null) {
    const coordText = m[0]
    const start = m.index

    if (start > lastIndex) {
      raw.push({ type: 'text', content: text.slice(lastIndex, start) })
    }

    if (!markerMap.has(coordText)) {
      const col = KR_COLS.indexOf(coordText[0])
      const num = parseInt(coordText.slice(1), 10)
      markerMap.set(coordText, {
        row: 19 - num,
        col,
        label: CIRCLED[count] ?? String(count + 1),
        coordText,
      })
      count++
    }

    raw.push({ type: 'coord', content: coordText, marker: markerMap.get(coordText)! })
    lastIndex = start + coordText.length
  }

  if (lastIndex < text.length) {
    raw.push({ type: 'text', content: text.slice(lastIndex) })
  }

  return mergeSequences(raw)
}

export function extractMarkersFromSegments(segments: TextSegment[]): CoordMarker[] {
  const seen = new Set<string>()
  const markers: CoordMarker[] = []
  for (const seg of segments) {
    if (seg.type === 'coord' && !seen.has(seg.marker.coordText)) {
      seen.add(seg.marker.coordText)
      markers.push(seg.marker)
    } else if (seg.type === 'sequence') {
      for (const mv of seg.moves) {
        if (!seen.has(mv.coordText)) {
          seen.add(mv.coordText)
          markers.push(mv)
        }
      }
    }
  }
  return markers
}
