# 진행 상황 (v3.2 기준 — 2026-04-13)

---

## 봇별 구현 현황

| 봇 | 파일 | Cog | 상태 | 비고 |
|----|------|-----|------|------|
| 먹구름봇 | `bot.py` | onboarding, summary, settings, time_settings, scheduler, weight* | ✅ 운영 | *weight 임시 |
| 메일봇 | `bot_mail.py` | email_monitor | ✅ 운영 | |
| 식사봇 | `bot_meal.py` | meal | ✅ 운영 | |
| 날씨봇 | `bot_weather.py` | weather | ✅ 운영 | |
| 체중관리봇 | `bot_weight.py` | (미로드) | 🔄 skeleton | cogs.weight 이전 필요 |
| 일기봇 | `bot_diary.py` | 미구현 | 📋 예정 | v3.4 |
| 일정봇 | `bot_schedule.py` | 미구현 | 📋 예정 | v3.5 |

---

## 구현 완료 (파일별)

### 봇 진입점

| 파일 | 내용 | 버전 |
|------|------|------|
| `bot.py` | 먹구름봇 — onboarding/summary/settings/time_settings/scheduler/weight(임시) 로드 | v3.2 |
| `bot_mail.py` | 메일봇 — email_monitor 단독 로드 | v3.1 |
| `bot_meal.py` | 식사봇 — cogs.meal 단독 로드 | v3.2 |
| `bot_weather.py` | 날씨봇 — cogs.weather 단독 로드 | v3.2 |
| `bot_weight.py` | 체중관리봇 skeleton — cogs.weight 미활성화 | 🔄 |

### Cogs

| 파일 | 내용 | 버전 |
|------|------|------|
| `cogs/onboarding.py` | 4필드 Modal, 쓰레드 5개 생성, Embed 전송, 식사 알림 Job 등록 | v3.2 |
| `cogs/time_settings.py` | Select Menu 2단계 시간 설정, 10분 단위, Job 재등록 | v2.4 |
| `cogs/meal.py` | 사진 입력 2경로, GPT Vision, 칼로리 0 차단 | v3.2 |
| `cogs/summary.py` | 오늘 요약 Ephemeral (칼로리/탄단지/끼니/GPT) | v2.9 |
| `cogs/weather.py` | 기상청+에어코리아, wake_time 스케줄러, 50개+ 도시 | v3.2 |
| `cogs/settings.py` | SettingsSubView (내정보/위치/시간/이메일 하위 메뉴) | v3.1 |
| `cogs/weight.py` | 체중 기록, 달성률 바, 목표 달성 판정 | v3.2 |
| `cogs/scheduler.py` | 22:00 판정, hourly decay, 식사 알림 3단계, ML 재학습, 주간 리포트 | v3.2 |
| `cogs/email_monitor.py` | 1분 IMAP 폴링, 스팸 필터, GPT 요약, 슬래시 커맨드 4종 | v3.1 |

### Utils

| 파일 | 내용 | 버전 |
|------|------|------|
| `utils/db.py` | 전체 CRUD + 마이그레이션 + 쓰레드 setter 6개 + meal_waiting 3개 | v3.2 |
| `utils/gpt.py` | GPT-4o 래퍼 (파싱/분석/대사/Vision/이메일요약) | v3.1 |
| `utils/embed.py` | 메인 Embed + 5버튼 + View/Modal 빌더 | v2.9 |
| `utils/image.py` | 11종 이미지 우선순위 선택 | v1.8 |
| `utils/ml.py` | 칼로리 보정 (즉시+Ridge/RF 개인화) | v2.6 |
| `utils/pattern.py` | 식습관 패턴 5종 탐지 | v2.6 |
| `utils/gpt_ml_bridge.py` | ML 결과 → GPT 프롬프트 주입 | v2.6 |
| `utils/badges.py` | 배지 7종, 달성 체크 | v2.7 |
| `utils/nutrition.py` | 식약처 API + GPT fallback | v2.8 |
| `utils/mail.py` | 네이버 IMAP/SMTP, 헤더 디코딩, KST 변환 | v3.1 |
| `utils/email_ui.py` | EmailSetupModal + SenderAddModal 공통 모달 | v3.1 |

---

## 미구현 / 진행 예정

### bot.py → 각 봇으로 이전 필요

| 항목 | 현재 위치 | 이전 대상 | 상태 |
|------|-----------|-----------|------|
| `cogs.weight` | bot.py (임시 로드) | bot_weight.py | 🔄 다음 작업 |
| `_weekly_ml_retrain` | cogs/scheduler.py | bot_meal.py | 📋 예정 |
| 주간 리포트 체중 섹션 | cogs/scheduler.py | bot_weight.py | 📋 예정 |
| 식사 알림 쓰레드 라우팅 | `_get_thread(thread_id)` | `meal_thread_id or thread_id` | 📋 예정 |

### 버그 / 안정화

| 우선순위 | 항목 | 파일 | 내용 |
|---------|------|------|------|
| P2 | `generate_comment_with_pattern()` 파라미터 불일치 | `utils/gpt_ml_bridge.py:73` | 미호출 데드코드, 수정 후 pattern 연동 활성화 |
| P2 | 식약처 숫자+단위 검색 500 오류 | `utils/nutrition.py` | 검색어 전처리 정규식 추가 |
| P2 | 여러 끼니 동시 입력 시 첫 번째만 저장 | `utils/embed.py MealInputModal` | 쉼표 분리 + 다중 파싱 |
| P2 | 사진 대기 만료 후 안내 메시지 없음 | `cogs/meal.py` | 만료 감지 → 재시도 안내 |

### 신규 봇 구현

| 봇 | 버전 | 상세 |
|----|------|------|
| 체중관리봇 분리 | v3.3 | [`docs/bots/weight/ROADMAP.md`](bots/weight/ROADMAP.md) |
| n8n 음식 추천 | v3.3 | [`docs/bots/mukgoorm/ROADMAP.md`](bots/mukgoorm/ROADMAP.md) Phase 3 |
| 일기봇 | v3.4 | [`docs/bots/diary/ROADMAP.md`](bots/diary/ROADMAP.md) |
| 일정봇 | v3.5 | [`docs/bots/schedule/ROADMAP.md`](bots/schedule/ROADMAP.md) |
| 오케스트레이터 전환 | v4.0 | [`docs/bots/mukgoorm/ROADMAP.md`](bots/mukgoorm/ROADMAP.md) Phase 4 |

---

## 완료된 이슈 (해결됨)

| 항목 | 해결 방법 | 버전 |
|------|-----------|------|
| 이메일 설정 후 기존 메일 재알림 | `set_email_credentials()` `initial_uid` 파라미터 추가, 설정 시 현재 최대 UID 저장 | v3.1 |
| `/이메일설정` 스레드 내 실행 시 `create_thread()` 오류 | `interaction.channel`이 Thread이면 `.parent` 사용 | v3.1 |
| 메일봇 이벤트 루프 공유 문제 | bot_mail.py 분리 → 독립 이벤트 루프 | v3.1 |
| 5분 폴링 지연 | 메일봇 분리 후 1분으로 단축 | v3.1 |
| 메일 발송 시각 미표시 | Date 헤더 파싱 → KST 변환 → embed `📅 발송 일시` 추가 | v3.1 |
| 이메일 모달 클래스 분산 | `utils/email_ui.py`로 공통 분리 | v3.1 |
| 식사 알림 스케줄러 미구현 | scheduler.py에 3단계 Job + hourly hunger decay 구현 | v2.2 |
| GPT 캐릭터 프롬프트 다마고치 고착 | 범용 캐릭터 설명으로 교체 | v2.1 |
| settings.py 칼로리 재계산 하드코딩 | gender/age/height를 DB에 저장하고 읽도록 수정 | v2.0 |
| 오늘 요약 식사 기록 조회 안 됨 | meals 날짜 쿼리 UTC→KST 이중변환 적용 | v2.3 |
| 메인 Embed 이미지 작게 표시됨 | set_thumbnail() 제거, 파일 첨부로 변경 | v2.3 |
| 식사 입력 중복 제출 → 동일 끼니 2회 저장 | `_meal_submitting` 집합으로 차단 | v2.8 |
| 칼로리 분석 GPT 의존 → 정확도 한계 | 식약처 식품영양성분 DB API 연동 | v2.8 |
| last_fed_at 미업데이트 → eat.png 미작동 | update_tamagotchi()에 last_fed_at 추가 | v2.7 |
| 게임성 부족 — 스트릭/배지 없음 | utils/badges.py 생성, nightly 배지 체크 | v2.7 |

---

## 알려진 버그 / 미완성

| 우선순위 | 항목 | 파일 | 설명 |
|---------|------|------|------|
| P2 | `generate_comment_with_pattern()` 파라미터 불일치 | `utils/gpt_ml_bridge.py:73` | 현재 미호출이라 크래시 없음. 추후 사용 시 수정 필요 |
| P2 | 식약처 검색어 정제 미구현 | `utils/nutrition.py` | 숫자+단위 포함 시 500 오류 → GPT fallback으로 처리됨 |
| P2 | 한 번에 여러 끼니 입력 시 첫 번째만 인식 | `utils/embed.py` MealInputModal | 다중 파싱 미구현 |
| 설계 한계 | ML ground truth 부재 | `utils/ml.py:134` | GPT 추정 칼로리를 학습 레이블로 사용 (circular) |

---

## 다음 작업 우선순위

```
[P1] 호스팅 배포
  → Railway / Render / VPS 중 선택
  → bot.py + bot_mail.py 동시 배포
  → .env → 플랫폼 시크릿 이전

[P2] 봇 추가 분리 (날씨봇, 일과봇)
  → 먹구름 아키텍처 멀티봇 전환 지속
```

---

## v3.2 변경 내역 (2026-04-13)

### 멀티봇 분리 — 식사봇 / 날씨봇 / 체중관리봇

| 파일 | 변경 내용 |
|------|-----------|
| `utils/db.py` | `meal_thread_id`, `weather_thread_id`, `weight_thread_id`, `meal_waiting_until` 컬럼 마이그레이션 추가 |
| `utils/db.py` | setter 6개 추가: `set_meal_thread_id`, `set_weather_thread_id`, `set_weight_thread_id`, `set_meal_waiting`, `clear_meal_waiting`, `is_meal_waiting` |
| `cogs/onboarding.py` | 온보딩 시 전용 쓰레드 3개 추가 생성 (식사 / 날씨 / 체중관리) → 총 5개 |
| `cogs/weather.py` | `update_weather_for_user()`: `weather_thread_id or thread_id` fallback 적용 |
| `cogs/weight.py` | 목표 달성 embed 전송: `weight_thread_id or thread_id` fallback 적용 |
| `utils/embed.py` | `photo_btn`: in-memory dict → `set_meal_waiting()` DB 기록으로 전환. 식사 전용 쓰레드 안내 |
| `cogs/meal.py` | `on_message`: `meal_thread_id or thread_id` fallback + `is_meal_waiting()` / `clear_meal_waiting()` DB 기반으로 전환 |
| `bot.py` | `cogs.weather`, `cogs.meal` 제거 (각 전용 봇으로 이전) |
| `bot_weather.py` | `cogs.weather` 로드 활성화 |
| `bot_meal.py` | `cogs.meal` 로드 활성화 |

### 설계 핵심 — 봇 간 상태 공유

기존에는 `MealPhotoCog.waiting` 딕셔너리(in-memory)로 사진 대기 상태를 관리했으나,
봇 프로세스가 분리되면서 cross-process 공유가 불가능해짐.
→ `users.meal_waiting_until TIMESTAMP` 컬럼으로 이전, DB를 단일 진실 공급원으로 사용.

```
[먹구름봇] 📸 버튼 → set_meal_waiting(user_id, 60s) → DB 기록
[식사봇  ] on_message → is_meal_waiting(user_id)    → DB 조회 → 감지
```

### 기존 유저 호환성 (Backward Compatibility)

온보딩 전 기존 유저는 새 쓰레드 ID가 NULL.
`weather_thread_id or thread_id` 패턴으로 기존 메인 쓰레드로 자동 fallback.
새로 온보딩하는 유저부터 전용 쓰레드 5개 생성.

---

## v3.1 변경 내역 (2026-04-13)

### 메일봇 분리 (아키텍처 개선)

| 파일 | 변경 내용 |
|------|-----------|
| `bot_mail.py` | 신규 — 메일 전용 봇 진입점. `DISCORD_TOKEN_EMAIL` 환경변수 사용 |
| `bot.py` | `email_monitor` cog 제거 (메일봇으로 이전) |
| `utils/email_ui.py` | 신규 — `EmailSetupModal`, `SenderAddModal` 공통 분리 |
| `cogs/email_monitor.py` | 모달 클래스 제거 → `utils.email_ui` import. 폴링 5분 → **1분** |
| `cogs/settings.py` | import 경로 `cogs.email_monitor` → `utils.email_ui` |

### 버그 수정

| 항목 | 파일 | 수정 내용 |
|------|------|-----------|
| 이메일 설정 시 기존 메일 재알림 | `utils/db.py` | `set_email_credentials()` `initial_uid` 파라미터 추가 |
| 스레드 내 `/이메일설정` 오류 | `utils/email_ui.py` | Thread 객체 감지 후 `.parent` 사용 |

### 기능 추가

| 기능 | 파일 | 내용 |
|------|------|------|
| 발송 일시 표시 | `utils/mail.py`, `cogs/email_monitor.py` | Date 헤더 → KST 변환 → embed `📅 발송 일시` 필드 |
| 본문 길이 기반 요약 분기 | `cogs/email_monitor.py` | ≤200자 원문 / >200자 GPT 요약 |

---

## v3.0 변경 내역 (2026-04-12)

### 이메일 모니터링 구현

- `cogs/email_monitor.py` 신규: APScheduler 5분 IMAP 폴링
- `utils/mail.py` 신규: 네이버 IMAP/SMTP 클라이언트
- `cogs/settings.py`: EmailSubView (발신자 추가/목록/삭제/수정) 추가
- `utils/db.py`: email 관련 테이블/함수 추가 (email_senders, email_log, set_email_credentials 등)
- `bot.py`: 메일 전용 스레드 자동 생성 로직

---

## v2.7~v2.9 신규 기능 요약

### 스트릭 + 도전과제 배지 (v2.7)
- `utils/badges.py`: 배지 7종 + `check_new_badges()` 체크 로직
- `cogs/scheduler.py` `_nightly_analysis()`: 스트릭 업데이트 + 배지 달성 시 골드 Embed

### 주간 리포트 (v2.7)
- `cogs/scheduler.py` `_weekly_report()`: 매주 일요일 08:00

### 식약처 API 연동 (v2.8)
- `utils/nutrition.py`: 식약처 식품영양성분 DB API, GPT fallback

### UI 개편 (v2.9)
- `utils/embed.py`: 5개 버튼, 하루 정리 통합, 설정 하위 메뉴
- `bot.py`: on_ready 중복 방지, 전체 유저 식사 알림 등록
