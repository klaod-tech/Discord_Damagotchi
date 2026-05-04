# 먹구름 (mukgoorm) — 프로젝트 문서 인덱스
version: 3.2 | last_updated: 2026-04-13 | branch: develop

---

## 루트 문서

| 파일 | 내용 |
|------|------|
| [TEAM_OVERVIEW.md](TEAM_OVERVIEW.md) | 팀 기술 개요서 — 프로젝트 소개, 기술 스택, 봇 구조, DB 스키마, 기능 흐름, 로드맵 전체 (신규 팀원 온보딩 시작점) |
| [01_OVERVIEW.md](01_OVERVIEW.md) | 기술 스택 상세, 환경변수, 버전 히스토리 (v1.0~v3.0) |
| [02_FLOWS.md](02_FLOWS.md) | 온보딩/식사/날씨/알림/설정/체중 기능 흐름 전체 |
| [03_DATABASE.md](03_DATABASE.md) | DB 스키마 (전체 테이블), 주요 CRUD 함수 목록 |
| [04_GAME_RULES.md](04_GAME_RULES.md) | hp/hunger/mood 수치 변화, 이미지 선택 우선순위 및 트리거 |
| [05_ML_MODULES.md](05_ML_MODULES.md) | ML 3개 모듈 (pattern/ml/bridge) 설명 및 로드맵 |
| [06_PROGRESS.md](06_PROGRESS.md) | 구현 완료 목록, 미구현/버그, v3.2 변경 내역 |
| [07_NEXT_FEATURES.md](07_NEXT_FEATURES.md) | n8n 음식 추천 (Phase 3), 아키텍처 로드맵 |
| [08_EMAIL.md](08_EMAIL.md) | 이메일 모니터링 상세 (IMAP 폴링, 스팸 필터, UI, 기술 구현) |

---

## 봇별 개발 문서 (`bots/`)

멀티봇 아키텍처 전용 문서. 봇 개발 시 이 폴더를 참조.

| 파일/폴더 | 내용 |
|----------|------|
| [bots/00_INDEX.md](bots/00_INDEX.md) | bots/ 폴더 전체 구조 및 Claude 세션 시작 가이드 |
| [bots/shared/](bots/shared/) | 공통 아키텍처 / DB 스키마 / 유틸리티 (모든 봇 개발 전 필독) |
| [bots/mukgoorm/](bots/mukgoorm/) | 먹구름봇 — 오케스트레이터, 버튼 허브, 스케줄러 |
| [bots/meal/](bots/meal/) | 식사봇 — 사진 감지, 칼로리 분석 |
| [bots/weather/](bots/weather/) | 날씨봇 — 기상청/에어코리아 API |
| [bots/weight/](bots/weight/) | 체중관리봇 — 체중 기록, 목표 추이 |
| [bots/email/](bots/email/) | 이메일봇 — IMAP 폴링, 발신자 알림 |
| [bots/diary/](bots/diary/) | 일기봇 — 감정 분석 (구현 예정, 코드 포함) |
| [bots/schedule/](bots/schedule/) | 일정봇 — 일정 등록/알림 (구현 예정, 코드 포함) |

---

## 새 협업자를 위한 빠른 시작

1. **프로젝트 전체 파악** → `TEAM_OVERVIEW.md` ← **여기서 시작**
2. **지금 뭐가 됐고 뭐가 남았는지** → `06_PROGRESS.md`
3. **특정 봇 개발** → `bots/00_INDEX.md` → 해당 봇 폴더
4. **DB 구조 상세** → `03_DATABASE.md`
5. **이미지/수치 규칙** → `04_GAME_RULES.md`

---

## 핵심 원칙 (항상 기억)

- **hp/hunger/mood 수치는 사용자에게 절대 직접 노출 금지** → 이미지+대사로만 표현
- **날씨는 별도 알림 없음** → 기상 시간에 이미지 자동 교체로만 전달
- **칼로리/영양소는 하루 정리 버튼 Ephemeral로만** 확인 가능
- **모든 개발은 `develop` 브랜치에서** → main은 배포용

---

## 빠른 참조

```
GitHub: https://github.com/klaod-tech/mukgoorm
개발 브랜치: develop
현재 버전: v3.2
DB: Supabase (PostgreSQL, psycopg2-binary)
AI: OpenAI GPT-4o
버튼 5개 (2행): [🍽️ 식사 입력] [📋 하루 정리] [🍜 뭐 먹고 싶어?] / [⚙️ 설정] [⚖️ 체중 기록]

실행 봇: bot.py / bot_mail.py / bot_meal.py / bot_weather.py
예정 봇: bot_weight.py (skeleton) / bot_diary.py / bot_schedule.py
```
