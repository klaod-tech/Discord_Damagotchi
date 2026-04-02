# 진행 상황 (v2.4 기준 — 2026-04-03)

## 구현 완료

| 파일 | 기능 | 상태 |
|------|------|------|
| `utils/db.py` | Supabase CRUD (users/tamagotchi/meals/weather_log/weight_log), gender/age/height 컬럼 추가 | ✅ 완료 |
| `utils/gpt.py` | GPT-4o 래퍼 (칼로리 계산, 식사 분석, 자연어 파싱, 대사 생성), 캐릭터 프롬프트 일반화 | ✅ 완료 |
| `utils/image.py` | 이미지 선택 로직 (우선순위 5단계, 11종 이미지) | ✅ 완료 |
| `utils/embed.py` | 메인 Embed + 6개 버튼 (2행) + MealInputModal + _send_daily_analysis, 칼로리 0 저장 차단 | ✅ 완료 |
| `utils/ml.py` | 칼로리 보정 모델 (양 표현 즉시 + Ridge/RF 개인화) | ✅ 완료 |
| `utils/pattern.py` | 식습관 패턴 분석 (5가지 패턴 탐지) | ✅ 완료 |
| `utils/gpt_ml_bridge.py` | ML 결과 → GPT 주입 브릿지 | ✅ 완료 |
| `cogs/onboarding.py` | 4필드 Modal, 쓰레드 생성, 첫 Embed 전송, TimeStep1View 유도, gender/age/height 저장, 식사 알림 Job 등록 | ✅ 완료 |
| `cogs/time_settings.py` | Select Menu 2단계 시간 설정, 분 10분 단위, 저장 시 식사 알림 Job 재등록 | ✅ 완료 |
| `cogs/meal.py` | 사진 입력 (on_message → GPT Vision → DB 저장), 칼로리 0 저장 차단 | ✅ 완료 |
| `cogs/summary.py` | 오늘 요약 (칼로리/탄단지/끼니별/GPT 코멘트) | ✅ 완료 |
| `cogs/weather.py` | 기상청+에어코리아 API, wake_time 기반 스케줄러 | ✅ 완료 |
| `cogs/settings.py` | 설정 변경 Modal (이름/도시/목표체중), 칼로리 재계산 시 DB 값 사용 | ✅ 완료 |
| `cogs/weight.py` | 체중 기록, 달성률 바, 목표 달성 판정 | ✅ 완료 |
| `cogs/scheduler.py` | 오후 10시 칼로리 판정, 매시간 hunger 감소, 유저별 식사 알림 3단계 Job | ✅ 완료 |
| `bot.py` | 봇 진입점, 8개 cog 로드, on_ready 시 전체 유저 식사 알림 Job 등록, 커맨드 실행 로깅 | ✅ 완료 |
| `requirements.txt` | psycopg2-binary 추가 | ✅ 완료 |

---

## 미구현

### P1 — ML 재학습 스케줄러 미등록
- `utils/ml.py`의 `retrain_all_users()`가 주 1회 APScheduler로 실행되어야 하나 아직 등록 안 됨
- **추가 필요**: `cogs/scheduler.py`에 매주 일요일 03:00 Job 추가

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
| psycopg2-binary requirements 누락 | requirements.txt에 추가 | v2.0 |
| weight_log 테이블 init_db 미등록 | init_db()에 CREATE TABLE 추가 | v2.0 |
| image.py 파일명 불일치 | 실제 이미지 파일명 기준으로 전면 수정 | v1.8 |

---

## 다음 작업 우선순위

```
[P1] ML 재학습 스케줄러 등록
  → cogs/scheduler.py에 매주 일요일 03:00 retrain_all_users() Job 추가

[P2] 호스팅 배포
  → Railway / Render / VPS 중 선택
  → .env → 플랫폼 시크릿 이전
  → develop → main 머지 후 배포
```

---

## 알려진 환경 이슈

| 항목 | 상태 |
|------|------|
| `.env` DATABASE_URL 설정 | Supabase URL 입력 필요 |
| `AIR_API_KEY` 환경변수명 | weather.py에서 `AIR_API_KEY` 사용 (AIRKOREA_API_KEY 아님) |
