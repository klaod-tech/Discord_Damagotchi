# 진행 상황 (v1.9 기준 — 2026-04-02)

## 구현 완료

| 파일 | 기능 | 상태 |
|------|------|------|
| `utils/db.py` | Supabase CRUD (users/tamagotchi/meals/weather_log/weight_log) | ✅ 완료 |
| `utils/gpt.py` | GPT-4o 래퍼 (칼로리 계산, 식사 분석, 자연어 파싱, 대사 생성) | ✅ 완료 |
| `utils/image.py` | 이미지 선택 로직 (우선순위 5단계, 11종 이미지) | ✅ 완료 |
| `utils/embed.py` | 메인 Embed + 6개 버튼 (2행) + MealInputModal + _send_daily_analysis | ✅ 완료 |
| `utils/ml.py` | 칼로리 보정 모델 (양 표현 즉시 + Ridge/RF 개인화) | ✅ 완료 |
| `utils/pattern.py` | 식습관 패턴 분석 (5가지 패턴 탐지) | ✅ 완료 |
| `utils/gpt_ml_bridge.py` | ML 결과 → GPT 주입 브릿지 | ✅ 완료 |
| `cogs/onboarding.py` | 4필드 Modal, 쓰레드 생성, 첫 Embed 전송, TimeStep1View 유도 | ✅ 완료 |
| `cogs/time_settings.py` | Select Menu 2단계 시간 설정 (TimeStep1View + TimeStep2View) | ✅ 완료 |
| `cogs/meal.py` | 사진 입력 (on_message → GPT Vision → DB 저장) | ✅ 완료 |
| `cogs/summary.py` | 오늘 요약 (칼로리/탄단지/끼니별/GPT 코멘트) | ✅ 완료 |
| `cogs/weather.py` | 기상청+에어코리아 API, wake_time 기반 스케줄러 | ✅ 완료 |
| `cogs/settings.py` | 설정 변경 Modal (이름/도시/목표체중) | ✅ 완료 |
| `cogs/weight.py` | 체중 기록, 달성률 바, 목표 달성 판정 | ✅ 완료 |
| `cogs/scheduler.py` | 오후 10시 칼로리 자동 판정 | ✅ 완료 |
| `bot.py` | 봇 진입점, 8개 cog 로드, setup/소환 명령어 | ✅ 완료 |

---

## 미구현 / 버그

### P1 — 이미지 파일 정리 (현재 작업 중)
- `images/` 폴더에 11개 이미지 있으나 파일명이 `image.py` 기대값과 불일치
- 전체 17종 필요 (현재 8종 누락: hungry, hungry_cry, overfed, underfed, sick, cold, cloudy, goal_achieved)
- **담당**: 파일명 최종 결정은 본인이 직접 진행 중

### P2 — 식사 알림 스케줄러 미구현
- `cogs/scheduler.py`에 오후 10시 칼로리 판정만 있음
- **추가 필요**: 각 유저의 breakfast/lunch/dinner 3단계 알림 Job
  - 식사시간 -30분 → 쓰레드 알림 메시지
  - 식사시간 정각 → Embed hungry.png 교체
  - 식사시간 +1시간 (미입력 시) → Embed hungry_cry.png 교체
- 참고: `docs/02_FLOWS.md` → 식사 알림 흐름 섹션

### P3 — settings.py 버그
- 목표 체중 변경 시 권장 칼로리 재계산 함수에 성별/나이/키/활동량이 하드코딩됨
  ```python
  # cogs/settings.py:122~129 — 현재 (버그)
  new_cal = await calculate_daily_calories(
      gender="남",  # 하드코딩
      age=25,       # 하드코딩
      height=170,   # 하드코딩
      activity="보통",  # 하드코딩
      ...
  )
  ```
- **수정 필요**: 온보딩 시 성별/나이/키/활동량을 DB에 저장하거나 GPT에 위임하는 방식으로 변경

### P4 — psycopg2 requirements.txt 누락
- `utils/db.py`가 psycopg2를 사용하지만 requirements.txt에 없음
- **수정 필요**: `requirements.txt`에 `psycopg2-binary>=2.9.0` 추가

### P5 — ML 재학습 스케줄러 미등록
- `utils/ml.py`의 `retrain_all_users()`가 주 1회 APScheduler로 실행되어야 하나 아직 등록 안 됨
- CONTEXT.md scheduler jobs: `{user_id}_ml_retrain` 매주 일요일 03:00

---

## 다음 작업 우선순위

```
[P1] 이미지 파일명 정리 ← 현재 진행 중 (본인 담당)
  → 파일명 결정 후 image.py와 매핑 확인

[P2] 식사 알림 스케줄러 구현
  → cogs/scheduler.py에 meal alert jobs 추가
  → 참고: docs/02_FLOWS.md → 식사 알림 흐름

[P3] requirements.txt에 psycopg2-binary 추가

[P4] settings.py 권장 칼로리 재계산 버그 수정

[P5] 호스팅 배포
  → Railway / Render / VPS 중 선택
  → .env → 플랫폼 시크릿 이전
  → develop → main 머지 후 배포
```

---

## 알려진 환경 이슈

| 항목 | 상태 |
|------|------|
| `.env` DATABASE_URL 설정 | Supabase URL 입력 필요 |
| `psycopg2` 설치 | `pip install psycopg2-binary` 필요 |
| `daily_cal_target` Supabase 값 | 현재 2400으로 설정됨 → 약 1900으로 수정 필요 |
| `AIR_API_KEY` 환경변수명 | weather.py에서 `AIR_API_KEY` 사용 (AIRKOREA_API_KEY 아님) |
