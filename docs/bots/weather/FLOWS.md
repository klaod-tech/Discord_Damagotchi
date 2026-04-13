# 날씨봇 — 날씨 알림 흐름

---

## 1. 봇 시작 시 Job 등록

```
bot_weather.py → on_ready()
  → WeatherCog.__init__()
  → _setup_jobs()
      → get_all_users()
      → 유저별 wake_time → _register_job_for_wake_time()
          → job_id = "weather_{HH}{MM}"
          → 이미 등록된 job_id → 스킵 (중복 방지)
          → scheduler.add_job(CronTrigger(hour, minute))
  → scheduler.add_job(_check_new_users, IntervalTrigger(minutes=10))
  → scheduler.start()
```

---

## 2. 온보딩 완료 시 Job 등록

```
먹구름봇 OnboardingModal.on_submit()
  → weather_cog = interaction.client.cogs.get("WeatherCog")
  → weather_cog.register_user_job(wake_time)
      → _register_job_for_wake_time(wake_time)
```

> 온보딩 봇(먹구름봇)과 날씨봇이 별개 프로세스이므로,  
> 날씨봇이 `WeatherCog`를 로드한 경우에만 등록됨.  
> 미등록 시 10분 후 `_check_new_users`가 자동으로 등록.

---

## 3. 날씨 업데이트 흐름 (매일 wake_time)

```
_run_weather_update(hour, minute)
  → wake_time = f"{hour:02d}:{minute:02d}"
  → get_all_users()
  → 유저별 user.wake_time == wake_time 인 경우:
      → update_weather_for_user(bot, user)

update_weather_for_user(bot, user)
  → thread_id = user.get("weather_thread_id") or user.get("thread_id")
  → guild.get_thread(thread_id)  ← 쓰레드 조회
  → _find_grid(city)  ← 도시 → 격자 좌표
  → fetch_weather(nx, ny)  ← 기상청 API
  → fetch_air(city)  ← 에어코리아 API
  → generate_comment(날씨 컨텍스트)
  → create_weather_log(...)  ← DB 저장
  → weather_thread.send(embed=weather_embed)  ← 날씨 Embed 전송
  → create_or_update_embed(
        thread, user, tama, comment,
        weather={weather, temp, pm10, pm25}
    )  ← 메인 Embed 이미지 교체
```

---

## 4. 이미지 선택 (날씨 기반)

날씨 기반 이미지 선택은 `utils/image.py`의 `_weather_image()` 담당:

| 조건 | 이미지 |
|------|--------|
| PM10 > 80 또는 PM25 > 35 | `wear mask.png` |
| 비/소나기 | `rainy.png` |
| 눈 | `snow.png` |
| 기온 ≥ 26°C | `hot.png` |
| 기온 ≤ 5°C | `warm.png` |
| 맑음/흐림 | None (감정 상태로 넘어감) |

> 날씨 이미지는 Embed 선택 우선순위 4순위 (배고픔보다 낮음)

---

## 5. 관리자 즉시 갱신 커맨드

```
!weather  (관리자 전용)
  → get_all_users() → 전체 유저 즉시 날씨 업데이트
```

---

## 6. 도시 → 격자 좌표 매핑

`CITY_GRID` 딕셔너리 (cogs/weather.py): 50개 도시 지원

```python
_find_grid(city: str) -> tuple[int, int]
# 1. 완전 일치 우선
# 2. 부분 일치 시 가장 긴 키 우선 (아산/안산 혼동 방지)
# 3. 모두 실패 시 서울(60, 127) 반환
```

---

## 7. 에어코리아 도시 → 시도 매핑

```python
# 특수 처리:
if city in ("아산", "천안", "공주", "논산", "보령"):
    sido = "충남"
# 그 외는 도시명의 광역시/도 기준으로 자동 매핑
```
