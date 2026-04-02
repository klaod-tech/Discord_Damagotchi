# 먹구름 (mukgoorm) — 프로젝트 컨텍스트 인덱스
version: 2.6 | last_updated: 2026-04-03 | branch: develop

---

## 문서 구조

| 파일 | 내용 |
|------|------|
| [01_OVERVIEW.md](01_OVERVIEW.md) | 프로젝트 개요, 기술 스택, 환경변수, 버전 히스토리 |
| [02_FLOWS.md](02_FLOWS.md) | 온보딩/식사/날씨/알림/설정/체중 기능 흐름 전체 |
| [03_DATABASE.md](03_DATABASE.md) | DB 스키마 (5개 테이블), 주요 CRUD 함수 목록 |
| [04_GAME_RULES.md](04_GAME_RULES.md) | hp/hunger/mood 수치 변화, 이미지 선택 우선순위 및 트리거 |
| [05_ML_MODULES.md](05_ML_MODULES.md) | ML 3개 모듈 (pattern/ml/bridge) 설명 및 로드맵 |
| [06_PROGRESS.md](06_PROGRESS.md) | 구현 완료 목록, 미구현/버그, 다음 작업 우선순위 |

---

## 새 협업자를 위한 빠른 시작

1. **프로젝트가 뭔지** → `01_OVERVIEW.md`
2. **어떻게 동작하는지** → `02_FLOWS.md`
3. **지금 뭐가 됐고 뭐가 남았는지** → `06_PROGRESS.md` ← **가장 중요**
4. **DB 구조** → `03_DATABASE.md`
5. **이미지/수치 규칙** → `04_GAME_RULES.md`
6. **ML 시스템** → `05_ML_MODULES.md`

---

## 핵심 원칙 (항상 기억)

- **hp/hunger/mood 수치는 사용자에게 절대 직접 노출 금지** → 이미지+대사로만 표현
- **날씨는 별도 알림 없음** → 기상 시간에 이미지 자동 교체로만 전달
- **칼로리/영양소는 오늘 요약 버튼 Ephemeral로만** 확인 가능
- **모든 개발은 `develop` 브랜치에서** → main은 배포용

---

## 빠른 참조

```
GitHub: https://github.com/klaod-tech/Discord_Damagotchi
개발 브랜치: develop
현재 버전: v2.6
DB: Supabase (PostgreSQL, psycopg2-binary)
AI: OpenAI GPT-4o
버튼 6개 (2행): [🍽️ 식사 입력] [📊 오늘 요약] [📅 오늘 일정] / [⚙️ 설정 변경] [⏰ 시간 설정] [⚖️ 체중 기록]
```
