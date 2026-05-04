# 날씨봇 (bot_weather.py) 제작 로드맵

> last_updated: 2026-04-13 | 현재 버전: v3.2 ✅ 운영 중

---

## 현재 상태 요약

### 구현 완료

- `bot_weather.py`: `cogs.weather` 단독 로드, `DISCORD_TOKEN_WEATHER` 사용
- `cogs/weather.py`: 기상청(KMA) + 에어코리아(AirKorea) API 연동
- 유저별 `wake_time` 기반 APScheduler 개인화 알림
- 50개+ 도시 → KMA 격자(nx, ny) 좌표 변환 테이블
- 이미지 우선순위 선택: 마스크 > 비/눈 > 더위/추위 > 맑음
- `weather_thread_id or thread_id` fallback 지원

### 이미지 선택 로직

```
PM10 > 80 또는 PM2.5 > 35  → wear_mask.png
강수형태 = 비               → rainy.png
강수형태 = 눈               → snow.png
기온 ≥ 26°C                → hot.png
기온 ≤ 5°C                 → warm.png (두껍게 입은 이미지)
하늘상태 = 흐림             → tired.png
하늘상태 = 구름많음          → smile.png
맑음                        → normal.png
```

### Embed 구성 (현재)

```
[캐릭터 이미지]
오늘 {이름}의 날씨 ☁️
날씨 상태 텍스트 (기온/강수 조합 한 줄 문장)
```

> 숫자(기온/PM10 수치)는 표시하지 않음 — 설계 원칙

---

## Phase 1 — 안정화 작업 (v3.2.x)

### 1-1. 도시 미지원 예외 처리

현재 `CITY_GRID` 딕셔너리에 없는 도시를 `users.city`로 설정한 경우 KeyError 발생 가능.

```python
# cogs/weather.py update_weather_for_user() 수정
grid = CITY_GRID.get(city)
if not grid:
    # 서울 기본값으로 fallback + 유저에게 안내
    grid = CITY_GRID["서울"]
    await thread.send(f"'{city}' 지역은 아직 지원되지 않아요. 서울 날씨로 대신 알려드릴게요.")
```

### 1-2. API 호출 실패 재시도

기상청 API 간헐적 5xx 오류 발생 시 현재 조용히 실패.  
→ 1회 재시도 + 실패 시 "날씨 정보를 가져오지 못했어요" 메시지.

```python
import asyncio

for attempt in range(2):
    try:
        weather_data = await fetch_kma(nx, ny)
        break
    except Exception as e:
        if attempt == 1:
            await thread.send("날씨 정보를 잠시 가져오지 못했어요. 잠시 후 다시 확인해주세요.")
            return
        await asyncio.sleep(5)
```

### 1-3. 새 유저 자동 스케줄 등록 확인

현재 `on_ready`에서 전체 유저 스케줄을 등록하나,  
온보딩 이후 새 유저가 생기면 다음 봇 재시작까지 날씨 알림 없음.

→ `cogs/onboarding.py`에서 온보딩 완료 후 날씨봇에 신호 필요 (Phase 2 태스크 큐 연동).  
→ 임시 해결: 날씨봇 `on_member_join` 이벤트 또는 1시간 주기 전체 유저 재등록.

```python
# cogs/weather.py — 1시간 주기 스케줄 점검
@scheduler.scheduled_job('interval', hours=1)
async def refresh_schedules():
    users = get_all_users()
    for user in users:
        job_id = f"weather_{user['user_id']}"
        if not scheduler.get_job(job_id):
            register_weather_job(user)
```

---

## Phase 2 — 날씨 상세 정보 추가 (v3.3)

### 2-1. 대기질 Embed 필드 추가

현재 이미지만으로 대기 상태 표현.  
→ "마스크가 필요한 날이에요" 같은 자연어 문장 추가 (수치 노출 금지).

```python
def _build_air_text(pm10: float, pm2_5: float) -> str:
    if pm10 > 150 or pm2_5 > 75:
        return "오늘은 미세먼지가 매우 나빠요. 외출 시 마스크는 필수예요!"
    if pm10 > 80 or pm2_5 > 35:
        return "미세먼지가 조금 있어요. 마스크를 챙겨가세요."
    if pm10 > 30 or pm2_5 > 15:
        return "보통 수준이에요. 그래도 조심하는 게 좋아요."
    return "공기가 맑아요. 오늘 산책하기 좋은 날이에요!"
```

### 2-2. 내일 날씨 미리보기 (옵션)

기상청 단기예보 API는 3일치 제공.  
Embed 하단에 "내일은 {내일날씨 텍스트}" 1줄 추가.

---

## Phase 3 — 도시 확장 (v3.3~v3.4)

### 3-1. 지원 도시 확대

현재 50개 → 100개+  
지방 소도시, 군/구 단위 추가:

```python
# cogs/weather.py CITY_GRID 추가 예시
"광교": {"nx": 60, "ny": 121},    # 수원 광교
"판교": {"nx": 62, "ny": 120},    # 성남 판교
"송도": {"nx": 54, "ny": 125},    # 인천 송도
```

### 3-2. 유저 도시 자동 검증

온보딩/설정 시 입력한 도시가 CITY_GRID에 없으면 즉시 안내:

```python
# cogs/settings.py 도시 설정 Modal 저장 시
if city not in CITY_GRID:
    supported = ", ".join(list(CITY_GRID.keys())[:10]) + " 등"
    await interaction.response.send_message(
        f"'{city}'는 아직 지원되지 않아요.\n지원 도시: {supported}",
        ephemeral=True
    )
    return
```

---

## Phase 4 — 오케스트레이터 연동 (v4.0)

### 4-1. 태스크 큐 폴링

```python
# cogs/weather.py — 30초 주기 폴링
@scheduler.scheduled_job('interval', seconds=30)
async def poll_weather_tasks():
    tasks = get_pending_tasks(bot_target='weather')
    for task in tasks:
        payload = json.loads(task['payload'])
        # 예: {"city": "제주도", "date": "2026-04-14"}
        await send_custom_weather(task['user_id'], payload)
        mark_task_done(task['task_id'])
```

---

## 주요 파일 위치

| 파일 | 역할 |
|------|------|
| `bot_weather.py` | 봇 진입점, `cogs.weather` 로드 |
| `cogs/weather.py` | KMA/AirKorea API 호출, 스케줄러, Embed 생성 |
| `utils/image.py` | 날씨 이미지 선택 로직 (우선순위 5단계) |
| `utils/db.py` | `create_weather_log()`, `set_weather_thread_id()`, `get_all_users()` |

---

## 환경변수

| 변수명 | 설명 |
|--------|------|
| `DISCORD_TOKEN_WEATHER` | 날씨봇 토큰 |
| `WEATHER_API_KEY` | 기상청(KMA) Open API 키 |
| `AIR_API_KEY` | 한국환경공단 에어코리아 API 키 |

---

## 설계 원칙 (변경 금지)

1. 기온/PM10/PM2.5 수치는 Embed에 절대 숫자로 표시하지 않음
2. 날씨 알림은 자동 — 유저가 명령하지 않아도 `wake_time`에 전송
3. 이미지 선택 우선순위: 마스크 > 강수 > 기온 > 하늘상태
4. `weather_thread_id or thread_id` fallback 항상 유지
