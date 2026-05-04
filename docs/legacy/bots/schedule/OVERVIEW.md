# 일정봇 — 오버뷰

> 현재 상태: 📋 구상 단계 — UX 흐름 미결, 코드 없음  
> 구현 전 UX 기획 구체화 필요

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_schedule.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_SCHEDULE` |
| 커맨드 prefix | `!schedule_` |
| 담당 Cog | `cogs/schedule.py` → `ScheduleCog` (신규 생성) |
| 응답 위치 | `users.personal_channel_id` (등록 응답), Push 알림 → `info_thread_id` |
| 담당 DB 테이블 | `schedule_log` (신규 생성 필요) |
| 슬래시 커맨드 | `/일정등록`, `/일정목록`, `/일정삭제` |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- 자연어 일정 등록 (GPT-4o 날짜/시간 파싱)
- 일정 D-day 알림 (APScheduler 5분 간격 체크)
- 반복 일정 지원 (daily/weekly/monthly/weekday)
- 일정 목록 조회 + 완료 체크
- 일정 삭제

### 이 봇이 하지 않는 것
- 날씨봇/식사봇 연계 일정 → 향후 오케스트레이터에서 처리
- 식사 계획 → 식사봇 담당

---

## 3. 슬래시 커맨드

| 커맨드 | 설명 | 응답 |
|--------|------|------|
| `/일정등록` | 자연어로 일정 등록 | ScheduleInputModal |
| `/일정목록` | 향후 7일 일정 조회 | Embed + 완료 체크 버튼 |
| `/일정삭제` | 일정 삭제 | Select Menu → 삭제 |

---

## 4. 반복 일정 규칙

| repeat_rule | 설명 |
|-------------|------|
| `none` (기본) | 반복 없음 |
| `daily` | 매일 |
| `weekly` | 매주 같은 요일 |
| `monthly` | 매달 같은 날 |
| `weekday` | 평일마다 |

---

## 5. 파일 구조 (구현 후)

```
bot_schedule.py     ← 봇 진입점
cogs/schedule.py    ← ScheduleCog, ScheduleInputModal, parse_schedule_input()
utils/db.py         ← schedule_log 테이블 + DB 함수 (마이그레이션 추가 필요)
```

---

## 6. 신규 구현 필요 항목 체크리스트

- [ ] `utils/db.py` — `schedule_log` 테이블 마이그레이션 추가
- [ ] `utils/db.py` — `personal_channel_id`, `info_thread_id` 컬럼은 v4.0 온보딩에서 이미 추가됨 (별도 불필요)
- [ ] `utils/db.py` — DB 함수 6개 추가
- [ ] `cogs/onboarding.py` — 일정 전용 쓰레드 생성 추가
- [ ] `cogs/schedule.py` — 신규 생성
- [ ] `bot_schedule.py` — `cogs.schedule` 로드 활성화
