# S0 사전 실험 결과

| 항목 | 내용 |
|------|------|
| 실험일 | 2026-10-04 |
| 상태 | mock 실행 완료 / 유단자 채점 대기 |

## 목적

20개 국면에 대해 KataGo 피처 + LLM 설명을 생성하고 유단자가 채점한다.
이 결과로 5종 이유 유형 분류 체계를 확정한다.

## 현재 상태

- `KATAGO_MOCK=true` 모드로 3개 국면 실행 완료
- 자충 감지 정상 동작 확인
- 실제 KataGo + Claude API 연동은 S2~S3에서 구현

## 이유 유형 가설 (확정 전)

| 코드 | 가설 빈도 |
|------|----------|
| `life_death` | 높음 (대마 싸움이 결정적 순간 비율 높음) |
| `cut_left` | 중간 |
| `missed_attack` | 중간 |
| `missed_big_point` | 중간 |
| `endgame_sente` | 낮음 (초반~중반 국면 위주) |

## 다음 단계

- [ ] 유단자 1명 섭외 (S0-6)
- [ ] 실제 대국 국면 20개 선정 (SGF 파일로 `fixtures/sgf/` 추가)
- [ ] 채점 시트 작성 (`eval/golden/scoring_template.jsonl`)
- [ ] KataGo 설치 후 실제 피처 추출 (S2)
