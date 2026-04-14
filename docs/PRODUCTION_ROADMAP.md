# 먹구름 전체 제작 로드맵

> last_updated: 2026-04-13 | 현재 버전: v3.2

---

## 봇별 현재 상태 한눈에 보기

| 봇 | 파일 | 담당 기능 | 현재 상태 | 다음 단계 |
|----|------|-----------|-----------|-----------|
| **먹구름봇** | `bot.py` | 온보딩, 설정, 식사텍스트, 스케줄러 | ✅ 운영 중 (v3.2) | 채널 구조 전환 + 오케스트레이터 전환 (v4.0) |
| **메일봇** | `bot_mail.py` | IMAP 폴링, 이메일 알림 | ✅ 운영 중 (v3.1) | 안정화 |
| **식사봇** | `bot_meal.py` | 사진 식사 감지, 칼로리 분석 | ✅ 운영 중 (v3.2) | n8n 음식 추천 연동 (웹훅 URL 수령 후) |
| **날씨봇** | `bot_weather.py` | 날씨/미세먼지 알림 | ✅ 운영 중 (v3.2) | 도시 확장 |
| **체중관리봇** | `bot_weight.py` | 체중 기록, 칼로리 목표 | 🔄 skeleton | cogs.weight 이전 후 기능 점진적 확장 |
| **일기봇** | `bot_diary.py` | 일기 작성, 감정 분석 | 📋 구상 단계 | UX 기획 구체화 → 구현 |
| **일정봇** | `bot_schedule.py` | 일정 등록, 알림 | 📋 구상 단계 | UX 기획 구체화 → 구현 |

---

## 전체 제작 순서 (Phase별)

```
Phase 1 ─ 호스팅 배포         (현재 → v3.2 안정화)
Phase 2 ─ 버그/안정화          (v3.2 → v3.2.x)
Phase 3 ─ 체중관리봇 분리       (v3.3 예정)
Phase 4 ─ n8n 음식 추천        (v3.3 예정)
Phase 5 ─ 일기봇               (v3.4 예정)
Phase 6 ─ 일정봇               (v3.5 예정)
Phase 7 ─ 오케스트레이터 전환   (v4.0)
```

---

## Phase 1 — 호스팅 배포

> 목표: 4개 봇 프로세스를 프로덕션 환경에서 동시 실행

### 사전 체크리스트

- [ ] 디스코드 Application 7개 생성 (봇마다 토큰 발급)
  - 먹구름봇 / 메일봇 / 식사봇 / 날씨봇 / 체중관리봇 / 일기봇 / 일정봇
- [ ] `.env` → 플랫폼 시크릿으로 이전
- [ ] `develop` → `main` 머지

### 배포 환경 선택 (Railway 권장)

| 옵션 | 장점 | 단점 |
|------|------|------|
| **Railway** | 다중 서비스 지원, Python 자동 감지 | 월 $5~20 |
| **Render** | 무료 플랜 있음 | 15분 슬립, 콜드 스타트 |
| **VPS (Vultr/DigitalOcean)** | 완전 통제 | 직접 관리 필요 |

Railway 기준 설정:
```yaml
# railway.toml 예시
[services.mukgoorm]
  startCommand = "python bot.py"
[services.mail]
  startCommand = "python bot_mail.py"
[services.meal]
  startCommand = "python bot_meal.py"
[services.weather]
  startCommand = "python bot_weather.py"
```

### 배포 후 검증

- [ ] 신규 유저 온보딩 → 쓰레드 5개 생성 확인
- [ ] 텍스트 식사 입력 → 칼로리 분석 확인
- [ ] 사진 식사 입력 → 60초 감지 확인
- [ ] 22:00 칼로리 판정 알림 확인
- [ ] 이메일 1분 폴링 확인
- [ ] 날씨 wake_time 알림 확인

---

## Phase 2 — 버그 수정 / 안정화

> 목표: P2 버그 해결, 안정적인 운영

### 작업 목록

| 우선순위 | 항목 | 파일 | 작업 내용 |
|---------|------|------|-----------|
| P2 | `generate_comment_with_pattern()` 파라미터 불일치 | `utils/gpt_ml_bridge.py:73` | 함수 시그니처 수정 후 pattern 연동 활성화 |
| P2 | 식약처 검색어 숫자+단위 500 오류 | `utils/nutrition.py` | 입력 전처리: 숫자·단위 제거 정규식 추가 |
| P2 | 여러 끼니 동시 입력 시 첫 번째만 인식 | `utils/embed.py MealInputModal` | 쉼표 분리 → 다중 파싱 구현 |
| P2 | meal_waiting_until 만료 전 재업로드 안내 미구현 | `cogs/meal.py` | 만료 감지 → "다시 📸 버튼 눌러주세요" 안내 |
| 모니터링 | Supabase 커넥션 풀 한계 | `utils/db.py` | 4봇 동시 연결 수 모니터링, 필요 시 pooling 파라미터 조정 |

---

## Phase 3 — 체중관리봇 분리 (v3.3)

> 목표: bot_weight.py 완전 활성화, 체중 전용 쓰레드로 분리

상세: [`docs/bots/weight/ROADMAP.md`](bots/weight/ROADMAP.md)

---

## Phase 4 — n8n 음식 추천 연동 (v3.3)

> 목표: `🍜 뭐 먹고 싶어?` 버튼 → n8n 웹훅 → 음식 추천 Embed

상세: [`docs/bots/mukgoorm/ROADMAP.md`](bots/mukgoorm/ROADMAP.md) Phase 3 참고

### 전제 조건

- [ ] n8n 팀원이 웹훅 URL 확정
- [ ] 응답 JSON 포맷 합의
- [ ] `address` 필드 추가 여부 결정 (구/동 단위 위치)

---

## Phase 5 — 일기봇 (v3.4)

> 목표: 감정 일기 작성, GPT 감정 분석, 주간 감정 리포트  
> 상태: 📋 구상 단계 — UX 흐름 미결, 구현 전 기획 구체화 필요

상세: [`docs/bots/diary/ROADMAP.md`](bots/diary/ROADMAP.md)

---

## Phase 6 — 일정봇 (v3.5)

> 목표: 일정 등록, 알림, 반복 패턴 관리  
> 상태: 📋 구상 단계 — UX 흐름 미결, 구현 전 기획 구체화 필요

상세: [`docs/bots/schedule/ROADMAP.md`](bots/schedule/ROADMAP.md)

---

## Phase 7 — 채널 구조 전환 + 오케스트레이터 (v4.0)

> 목표:
> 1. 유저별 전용 채널 + 기능봇 쓰레드 구조로 온보딩 전환
> 2. bot.py가 GPT/ML 의도 파싱으로 전문봇 자동 트리거
> 3. intent_log 데이터 축적 → ML 의도 분류기 점진적 전환

상세: [`docs/bots/mukgoorm/ROADMAP.md`](bots/mukgoorm/ROADMAP.md) Phase 3.5~5 참고

### 인프라 고려 사항 (20인 서버 기준)

| 항목 | 내용 |
|------|------|
| Discord 채널 수 | 최대 20명 × (채널 1개 + 쓰레드 2개) ≈ 60개 (한도 500, 여유 있음) |
| 환경변수 추가 | `TAMAGOTCHI_CATEGORY_ID` (카테고리 ID) |
| DB 컬럼 추가 | `users.personal_channel_id`, `users.address` |
| 신규 테이블 | `task_queue` (봇 간 통신 + result_json 반환), `intent_log` (ML 학습 데이터) |
| Supabase 연결 | 7개 봇 동시 운영 → 커넥션 풀 한도 확인 필요 |

---

## 봇 간 DB 공유 구조

```
모든 봇 → utils/db.py → Supabase PostgreSQL (Session Pooler)

소유 관계:
  bot.py        → users, tamagotchi, meals(text), badges
  bot_meal.py   → meals(photo)
  bot_weather.py→ weather_log
  bot_weight.py → weight_log
  bot_mail.py   → email_senders, email_log
  bot_diary.py  → diary_log         (신규)
  bot_schedule.py → schedules       (신규)
```

---

## 환경변수 현황

| 변수명 | 상태 | 사용 봇 |
|--------|------|---------|
| `DISCORD_TOKEN` | ✅ 있음 | bot.py |
| `DISCORD_TOKEN_EMAIL` | ✅ 있음 | bot_mail.py |
| `DISCORD_TOKEN_MEAL` | ✅ 있음 | bot_meal.py |
| `DISCORD_TOKEN_WEATHER` | ✅ 있음 | bot_weather.py |
| `DISCORD_TOKEN_WEIGHT` | 📋 발급 필요 | bot_weight.py |
| `DISCORD_TOKEN_DIARY` | 📋 발급 필요 | bot_diary.py |
| `DISCORD_TOKEN_SCHEDULE` | 📋 발급 필요 | bot_schedule.py |
| `OPENAI_API_KEY` | ✅ 있음 | 전체 |
| `WEATHER_API_KEY` | ✅ 있음 | bot_weather.py |
| `AIR_API_KEY` | ✅ 있음 | bot_weather.py |
| `FOOD_API_KEY` | ✅ 있음 | bot_meal.py |
| `DATABASE_URL` | ✅ 있음 | 전체 |
| `TAMAGOTCHI_CHANNEL_ID` | ✅ 있음 | 전체 |
| `N8N_FOOD_WEBHOOK_URL` | 📋 웹훅 URL 수령 후 등록 | bot.py |
| `TAMAGOTCHI_CATEGORY_ID` | 📋 v4.0 채널 구조 전환 시 | bot.py |
