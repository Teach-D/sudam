export interface CoordMarker {
  row: number
  col: number
  label: string
  coordText: string
}

export type TextSegment =
  | { type: 'text'; content: string }
  | { type: 'coord'; content: string; marker: CoordMarker }

const KR_COLS = '가나다라마바사아자차카타파하거너더러머'
// 한국식 좌표: 열(가~머) + 행(1~19). 19부터 먼저 시도해 "가19"를 "가1"+"9"로 쪼개지 않게 한다.
const COORD_RE = /[가나다라마바사아자차카타파하거너더러머](?:19|1[0-8]|[1-9])/g
const CIRCLED = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩']

export function splitWithCoords(text: string): TextSegment[] {
  const segments: TextSegment[] = []
  const markerMap = new Map<string, CoordMarker>()
  let count = 0
  let lastIndex = 0

  COORD_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = COORD_RE.exec(text)) !== null) {
    const coordText = m[0]
    const start = m.index

    if (start > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, start) })
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

    segments.push({ type: 'coord', content: coordText, marker: markerMap.get(coordText)! })
    lastIndex = start + coordText.length
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) })
  }

  return segments
}

export function extractMarkersFromSegments(segments: TextSegment[]): CoordMarker[] {
  const seen = new Set<string>()
  const markers: CoordMarker[] = []
  for (const seg of segments) {
    if (seg.type === 'coord' && !seen.has(seg.marker.coordText)) {
      seen.add(seg.marker.coordText)
      markers.push(seg.marker)
    }
  }
  return markers
}
