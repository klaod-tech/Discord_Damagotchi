# 날씨봇 — 오버뷰

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_weather.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_WEATHER` |
| 커맨드 prefix | `!weather_` |
| 담당 Cog | `cogs/weather.py` → `WeatherCog` |
| 담당 쓰레드 | `users.weather_thread_id` (fallback: `thread_id`) |
| 담당 DB 테이블 | `weather_log` (소유) |
| 현재 상태 | ✅ cog 구현 완료 |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- 유저 기상 시간(wake_time)에 날씨 데이터 자동 수집
- 기상청 초단기실황 API (격자 좌표 기반)
- 에어코리아 미세먼지 API (시도 기반)
- 날씨 전용 쓰레드에 날씨 Embed 전송
- 다마고치 메인 Embed 이미지를 날씨 기반으로 교체
- `weather_log` DB 저장 (먹구름봇 하루정리에서 읽음)
- `!weather` 커맨드 (관리자 전용 즉시 갱신)
- 매 10분마다 새 유저 wake_time Job 자동 등록

### 이 봇이 하지 않는 것
- 날씨 별도 알림 없음 — 기상 시간에 이미지 자동 교체로만 전달 (**절대 불변 원칙**)
- 슬래시 커맨드 없음 (버튼/스케줄러 기반)

---

## 3. 스케줄러 구조

```
AsyncIOScheduler
  └── 유저별 wake_time Job (CronTrigger)
        job_id: "weather_{HH}{MM}"
        → _run_weather_update(hour, minute)
            → 해당 wake_time 유저 전체에 update_weather_for_user()

  └── _check_new_users (IntervalTrigger, 10분)
        → 새 유저의 wake_time Job 자동 등록
```

**Job 중복 방지**: `_registered_jobs: set[str]` — 동일 wake_time Job 중복 등록 방지

---

## 4. 날씨 Embed 출력 형식

```
{icon} 오늘의 날씨 — {city}
━━━━━━━━━━━━━━━━━━━━━━
🌡️ 날씨 / 기온: {weather} / {temp}°C
💨 미세먼지: PM10: {pm10} | PM2.5: {pm25}
             등급: {pm_grade}
💬 {tama_name} 한마디: *{comment}*
━━━━━━━━━━━━━━━━━━━━━━
푸터: 좋은 아침이야! 오늘도 파이팅 🌱
```

---

## 5. 파일 구조

```
bot_weather.py   ← 봇 진입점
cogs/weather.py  ← WeatherCog (스케줄러, API 호출, Embed 전송)
utils/db.py      ← create_weather_log, get_latest_weather
```
