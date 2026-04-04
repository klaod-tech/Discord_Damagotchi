# 진행 상황 (v2.7 기준 — 2026-04-04)

## 구현 완료

| 파일 | 기능 | 상태 |
|------|------|------|
| `utils/db.py` | Supabase CRUD (users/tamagotchi/meals/weather_log/weight_log), gender/age/height 컬럼 추가 | ✅ 완료 |
| `utils/gpt.py` | GPT-4o 래퍼 (칼로리 계산, 식사 분석, 자연어 파싱, 대사 생성), 캐릭터 프롬프트 일반화 | ✅ 완료 |
| `utils/image.py` | 이미지 선택 로직 (우선순위 5단계, 11종 이미지) | ✅ 완료 |
| `utils/embed.py` | 메인 Embed + 6개 버튼 (2행) + MealInputSelectView (텍스트/사진 선택) + MealInputModal + _send_daily_analysis, 칼로리 0 저장 차단 | ✅ 완료 |
| `utils/ml.py` | 칼로리 보정 모델 (양 표현 즉시 + Ridge/RF 개인화) | ✅ 완료 |
| `utils/pattern.py` | 식습관 패턴 분석 (5가지 패턴 탐지) | ✅ 완료 |
| `utils/gpt_ml_bridge.py` | ML 결과 → GPT 주입 브릿지 | ✅ 완료 |
| `cogs/onboarding.py` | 4필드 Modal, 쓰레드 생성, 첫 Embed 전송, TimeStep1View 유도, gender/age/height 저장, 식사 알림 Job 등록 | ✅ 완료 |
| `cogs/time_settings.py` | Select Menu 2단계 시간 설정, 분 10분 단위, 저장 시 식사 알림 Job 재등록 | ✅ 완료 |
| `cogs/meal.py` | 사진 입력 2경로 (버튼 60초 대기 / 직접 업로드), _build_analysis_embed 헬퍼, MealPhotoCog.waiting 상태 관리, 칼로리 0 저장 차단 | ✅ 완료 |
| `cogs/summary.py` | 오늘 요약 (칼로리/탄단지/끼니별/GPT 코멘트) | ✅ 완료 |
| `cogs/weather.py` | 기상청+에어코리아 API, wake_time 기반 스케줄러 | ✅ 완료 |
| `cogs/settings.py` | 설정 변경 Modal (이름/도시/목표체중), 칼로리 재계산 시 DB 값 사용 | ✅ 완료 |
| `cogs/weight.py` | 체중 기록, 달성률 바, 목표 달성 판정 | ✅ 완료 |
| `cogs/scheduler.py` | 오후 10시 칼로리 판정, 매시간 hunger 감소, 유저별 식사 알림 3단계 Job, 매주 일요일 03:00 ML 재학습, 일요일 08:00 주간 리포트, 스트릭/배지 nightly 체크 | ✅ 완료 |
| `utils/badges.py` | 배지 7종 정의, 스트릭·DB 기반 신규 배지 체크 로직 | ✅ 완료 |
| `bot.py` | 봇 진입점, 8개 cog 로드, on_ready 시 전체 유저 식사 알림 Job 등록, 커맨드 실행 로깅 | ✅ 완료 |
| `requirements.txt` | psycopg2-binary 추가 | ✅ 완료 |

---

## 미구현

### P1 — 호스팅 배포
- Railway / Render / VPS 중 선택
- `.env` → 플랫폼 시크릿 이전
- `develop` → `main` 머지 후 배포

### v2.8 — 신규 기능 (설계 중)
상세 내용: [`07_NEXT_FEATURES.md`](07_NEXT_FEATURES.md)
- **버튼 UI 개편**: 오늘 요약 + 오늘 일정 → `📋 하루 정리` 통합 / 설정 하위 메뉴 구조화
- **n8n 음식 추천**: `🍜 뭐 먹고 싶어?` 버튼 → n8n 웹훅 POST → 위치·식사이력 기반 추천
- **위치 정보 상세화**: 음식 추천용 구/동 단위 주소 필드 추가 (옵션 결정 중)

---

## 완료된 이슈 (해결됨)

| 항목 | 해결 방법 | 버전 |
|------|-----------|------|
| 식사 알림 스케줄러 미구현 | scheduler.py에 3단계 Job + hourly hunger decay 구현 | v2.2 |
| utils/cogs/ 데드코드 | 디렉토리 삭제 | v2.2 |
| 프로젝트명 미확정 | 먹구름(mukgoorm) 확정, 서비스 노출 문구 전면 수정 | v2.1 |
| GPT 캐릭터 프롬프트 다마고치 고착 | 범용 캐릭터 설명으로 교체 | v2.1 |
| settings.py 칼로리 재계산 하드코딩 | gender/age/height를 DB에 저장하고 읽도록 수정 | v2.0 |
| users 테이블 gender/age/height 컬럼 누락 | init_db() 마이그레이션에 ADD COLUMN IF NOT EXISTS 추가 | v2.3 |
| 오늘 요약 식사 기록 조회 안 됨 | meals 날짜 쿼리 UTC→KST 이중변환 적용 (`AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'`) | v2.3 |
| 메인 Embed 이미지 작게 표시됨 | set_thumbnail() 제거, 파일 첨부로 이미지 크게 표시되도록 변경 | v2.3 |
| 오늘 요약 footer 불필요 | 개인 쓰레드에서 ephemeral footer 제거 | v2.4 |
| 시간 설정 분 단위 30분 → 10분 | _minute_options 10분 단위 6개로 변경, placeholder 구역 레이블 추가 | v2.4 |
| 식사 입력 사진 경로 버튼 미연결 | MealInputSelectView 추가, 버튼 클릭 → 60초 대기 → on_message 즉시 분석 | v2.5 |
| "남은 거리" 용어 부자연스러움 | embed.py, weight.py → "남은 몸무게"로 수정 | v2.5 |
| 오늘 일정 날씨 지역 미표시 | 날씨 텍스트에 📍 도시명 추가 | v2.5 |
| ML 재학습 스케줄러 미등록 | scheduler.py에 매주 일요일 03:00 _weekly_ml_retrain() Job 등록 | v2.6 |
| `last_fed_at` 미업데이트 → eat.png 미작동 | meal.py, embed.py의 update_tamagotchi() 호출에 `last_fed_at` 추가, datetime import 추가 | v2.7 |
| 게임성 부족 — 스트릭/배지 없음 | utils/badges.py 생성, scheduler nightly에 스트릭 업데이트 + 배지 체크 + cheer.png 갱신 추가 | v2.7 |
| 주간 리포트 없음 | scheduler.py 일요일 08:00 _weekly_report() 추가 (칼로리/끼니/체중/스트릭/배지 요약) | v2.7 |
| users 테이블 streak/max_streak/badges 컬럼 누락 | init_db() 마이그레이션에 ALTER TABLE IF NOT EXISTS 추가 | v2.7 |
| 이미지 11종 동작 검증 | images/ 폴더 파일 존재 확인, IMAGE_DESCRIPTIONS 키 매핑 전수 검사 완료 | v2.6 |
| 오늘 일정 footer 미제거 | embed.py schedule_button의 ephemeral footer 제거 | v2.6 |
| psycopg2-binary requirements 누락 | requirements.txt에 추가 | v2.0 |
| weight_log 테이블 init_db 미등록 | init_db()에 CREATE TABLE 추가 | v2.0 |
| image.py 파일명 불일치 | 실제 이미지 파일명 기준으로 전면 수정 | v1.8 |

---

## 알려진 버그 / 미완성

| 우선순위 | 항목 | 파일 | 설명 |
|---------|------|------|------|
| P2 | `generate_comment_with_pattern()` 파라미터 불일치 | `utils/gpt_ml_bridge.py:73` | `generate_comment()` 시그니처(`context`, `user`, `today_calories`, `recent_meals`)와 다른 파라미터로 호출 → 현재 이 함수는 어디서도 호출되지 않아 크래시 없음. 추후 사용 시 수정 필요 |
| 설계 한계 | ML ground truth 부재 | `utils/ml.py:134` | 개인화 모델이 GPT 추정 칼로리를 학습 레이블로 사용 (circular). 실제 체중 변화(`weight_log`)와 연동하는 방식은 ML 로드맵의 2순위 항목으로 별도 구현 예정 |

---

## 다음 작업 우선순위

```
[P1] 호스팅 배포
  → Railway / Render / VPS 중 선택
  → .env → 플랫폼 시크릿 이전
  → develop → main 머지 후 배포
```

---

## v2.7 신규 기능 요약

### 스트릭 + 도전과제 배지
- `utils/badges.py`: 배지 7종 정의 + `check_new_badges()` 체크 로직
- `utils/db.py`: `users` 테이블에 `streak`, `max_streak`, `badges` 컬럼 추가
  - `update_streak()`, `add_badges()`, `get_weekly_meal_stats()` 헬퍼 추가
- `cogs/scheduler.py` `_nightly_analysis()`:
  - 오늘 식사 기록 있으면 `streak + 1`, 없으면 0 초기화
  - `check_new_badges()` → 신규 배지 있으면 골드 Embed 발송 + `cheer.png` 메인 Embed 갱신
  - 스트릭 3일 이상이었다가 끊기면 아쉬운 메시지 전송

| 배지 ID | 조건 |
|---------|------|
| `first_meal` | 첫 식사 기록 |
| `streak_3` | 3일 연속 |
| `streak_7` | 7일 연속 |
| `streak_30` | 30일 연속 |
| `calorie_10` | 목표 칼로리 달성 10일 |
| `photo_10` | 사진 입력 10회 |
| `morning_7` | 아침 기록 7회 |

### 주간 리포트
- `cogs/scheduler.py` `_weekly_report()`: 매주 일요일 08:00 자동 발송
- 포함 항목: 평균 칼로리 / 끼니 커버리지(아침·점심·저녁) / 이번 주 최다 음식 / 체중 변화 / 연속 기록 / 보유 배지 / GPT 주간 코멘트

---

## 알려진 환경 이슈

| 항목 | 상태 |
|------|------|
| `.env` DATABASE_URL 설정 | Supabase URL 입력 필요 |
| `AIR_API_KEY` 환경변수명 | weather.py에서 `AIR_API_KEY` 사용 (AIRKOREA_API_KEY 아님) |
