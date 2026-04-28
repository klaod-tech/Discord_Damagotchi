# 변경사항 정리 — 2026-04-28

주요 버그 6종 수정. 변경 파일: `utils/embed.py`, `cogs/scheduler.py`, `utils/db.py`, `cogs/onboarding.py`, `cogs/meal.py`

---

## 1. `utils/embed.py` — `asyncio.sleep` 블로킹 제거

### 핵심 개념: `await` vs `asyncio.create_task`

| | `await asyncio.sleep(180)` (기존) | `asyncio.create_task(...)` (변경 후) |
|---|---|---|
| 동작 | 현재 코루틴이 180초 동안 멈춤 | 백그라운드에서 독립 실행, 즉시 반환 |
| 문제 | Modal handler가 3분간 메모리·루프 점유 | 없음 |
| 중첩 | 유저가 여러 번 입력하면 여러 sleep이 동시에 쌓임 | 태스크가 독립적으로 분리됨 |

### 변경 내용

**추가:** `_post_meal_embed` 헬퍼 함수 신설 (`utils/embed.py:111`)

```python
async def _post_meal_embed(thread, user, user_id, food_name, delay=60):
    await asyncio.sleep(delay)          # 60초 대기 (기존 180초)
    tama_final = get_tamagotchi(user_id)
    comment_after = await gc(...)       # GPT 대사 생성
    await create_or_update_embed(...)   # embed 갱신
```

**변경:** `MealInputModal.on_submit` 내부 sleep 블록 10줄 → `create_task` 1줄

```python
# 기존 (10줄, await로 묶임)
await asyncio.sleep(180)
tama_final = get_tamagotchi(user_id)
from utils.gpt import generate_comment as gc
comment_after = await gc(context="...", ...)
await create_or_update_embed(thread, user, tama_final, comment_after)

# 변경 후 (3줄, 백그라운드 태스크)
asyncio.create_task(
    _post_meal_embed(thread, user, user_id, food_name)
)
```

**효과:** 식사 입력 시 Modal handler가 즉시 종료되고, embed 후속 업데이트는 60초 후 백그라운드에서 실행됨.

---

## 2. `cogs/scheduler.py` — 아카이브 쓰레드 조회 실패 수정

### 문제

`guild.get_thread(id)`는 봇 메모리 캐시에 있는 쓰레드만 반환함.
Discord 쓰레드는 **7일 무활동 시 자동 보관(archive)**되며, 봇 재시작 후에도 캐시가 초기화됨.
→ 모든 스케줄 알림(`_meal_reminder`, `_meal_upset`, `_meal_late`, `_nightly_analysis`, `_weekly_report`)이 쓰레드를 찾지 못하고 조용히 실패했음.

### 변경 내용

**`_get_thread` 메서드** (`cogs/scheduler.py:468`)

```python
# 기존 (캐시만 확인)
for guild in self.bot.guilds:
    thread = guild.get_thread(thread_id)
    if thread:
        return thread
return None

# 변경 후 (캐시 실패 시 fetch로 재확인)
for guild in self.bot.guilds:
    thread = guild.get_thread(thread_id)
    if thread:
        return thread
    try:
        channel = await guild.fetch_channel(thread_id)   # API 직접 호출
        if isinstance(channel, discord.Thread):
            return channel
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        continue
return None
```

**효과:** 아카이브된 쓰레드, 봇 재시작 후에도 스케줄 알림이 정상 발송됨.

---

## 3. `utils/db.py` — INTERVAL SQL 버그 + `update_user` 안전 가드

### 3-1. INTERVAL 파라미터 버그 (`utils/db.py:595`)

```python
# 기존 (버그 — %s가 SQL 문자열 리터럴 안에 있어 바인딩 미적용)
"UPDATE users SET meal_waiting_until = NOW() + INTERVAL '%s seconds' WHERE user_id = %s"

# 변경 후 (올바른 파라미터 바인딩)
"UPDATE users SET meal_waiting_until = NOW() + (%s * INTERVAL '1 second') WHERE user_id = %s"
```

**효과:** 사진 입력 대기 기능(`📸 사진으로 입력` → 60초 타이머)이 실제로 동작함.

### 3-2. `update_user` 빈 kwargs 가드 (`utils/db.py:209`)

```python
# 기존 (kwargs 비어있으면 "UPDATE users SET  WHERE ..." SQL 구문 오류 발생)
def update_user(user_id, **kwargs):
    conn = get_conn()
    ...

# 변경 후
def update_user(user_id, **kwargs):
    if not kwargs:
        return
    conn = get_conn()
    ...
```

---

## 4. `cogs/onboarding.py` — 기존 유저 데이터 리셋 위험 수정

### 문제

`start_button` 클릭 시 `guild.get_thread()`로 기존 쓰레드 존재 여부를 확인함.
아카이브된 쓰레드는 캐시에 없어 `None`이 반환되므로, **이미 등록된 유저도 OnboardingModal이 열렸음.**
`OnboardingModal.on_submit`에서 `create_user()`(UPSERT)와 `create_tamagotchi()`(UPSERT + hp/hunger/mood 초기화)가 실행되어 **타마고치 수치와 설정이 리셋**될 수 있었음.

### 변경 내용

```python
# 기존
thread = guild.get_thread(int(existing["thread_id"]))
if thread:
    await interaction.response.send_message("이미 등록되어 있어! ...")
    return

# 변경 후 (캐시 실패 시 fetch로 재확인 + guild None 가드)
guild = interaction.guild
if guild:
    existing_thread = guild.get_thread(int(existing["thread_id"]))
    if existing_thread is None:
        try:
            ch = await guild.fetch_channel(int(existing["thread_id"]))
            if isinstance(ch, discord.Thread):
                existing_thread = ch
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            existing_thread = None
    if existing_thread:
        await interaction.response.send_message("이미 등록되어 있어! ...")
        return
```

**효과:** 아카이브된 쓰레드가 있는 유저도 재온보딩 팝업이 뜨지 않아 데이터가 보호됨.

---

## 5. `cogs/meal.py` — `on_timeout` 버튼 비활성화 미적용 수정

### 문제

```python
# 기존 — Python 메모리만 수정, Discord 메시지는 그대로
async def on_timeout(self):
    for child in self.children:
        child.disabled = True
```

`View.on_timeout()`은 Discord 메시지를 자동으로 수정하지 않음.
→ 만료 후에도 유저 화면에서 버튼이 클릭 가능한 상태로 남아있었음.

### 변경 내용

**`MealPhotoDetectView` 및 `MealPhotoConfirmView` 두 클래스 모두:**

1. `__init__`에 메시지 참조 필드 추가:
```python
self.message: discord.Message | None = None
```

2. `on_timeout` 수정:
```python
async def on_timeout(self):
    for child in self.children:
        child.disabled = True
    if self.message:
        try:
            await self.message.edit(view=self)   # 실제 Discord 메시지 업데이트
        except discord.HTTPException:
            pass
```

3. 메시지 발송 시 참조 저장 (3곳):
```python
# MealPhotoCog.on_message — 감지 메시지
detect_view = MealPhotoDetectView(user_id=user_id, image_url=image_url)
detect_msg = await message.channel.send("📸 음식 사진이에요?", view=detect_view)
detect_view.message = detect_msg

# MealPhotoDetectView.analyze — 분석 결과 메시지
confirm_msg = await interaction.followup.send(embed=embed, view=confirm_view)
confirm_view.message = confirm_msg

# MealPhotoCog.on_message(is_meal_waiting 경로) — 분석 결과 메시지
confirm_msg = await message.channel.send(embed=embed, view=confirm_view)
confirm_view.message = confirm_msg
```

**효과:** 버튼 만료(120초/180초) 후 Discord 메시지에서도 버튼이 회색으로 비활성화됨.

---

## 변경 파일 요약 (세션 1)

| 파일 | 변경 줄 수 | 주요 변경 |
|------|-----------|-----------|
| `utils/embed.py` | +22 / -10 | `_post_meal_embed` 추가, `await sleep` → `create_task` |
| `cogs/scheduler.py` | +6 / 0 | `fetch_channel` 폴백 추가 |
| `utils/db.py` | +2 / -1 | INTERVAL 버그 수정, 빈 kwargs 가드 |
| `cogs/onboarding.py` | +9 / -4 | fetch 폴백 + guild null 가드 |
| `cogs/meal.py` | +18 / -3 | `self.message` + `on_timeout` edit + 참조 저장 3곳 |

---

# 변경사항 정리 — 2026-04-28 (세션 2)

버그 3종 수정. 변경 파일: `utils/gpt.py`, `cogs/meal.py`, `utils/embed.py`, `utils/thread_helper.py`(신규), `bot_meal.py`, `bot_weather.py`, `bot_mail.py`, `bot_weight.py`

---

## 6. `utils/gpt.py` — 여러 끼니 동시 입력 파싱 미지원 수정

### 문제

`parse_meal_input`이 단일 `dict`를 반환하는 구조라, "오늘 아침 치킨 먹었어. 오늘 점심은 샌드위치 2개 먹었어" 입력 시 첫 번째 끼니(아침 치킨)만 인식됨.

### 변경 내용

```python
# 기존 — 단일 dict 반환
async def parse_meal_input(raw_text: str) -> dict:
    prompt = "... {days_ago: ..., meal_type: ..., food_name: ...}"
    ...
    return {"days_ago": ..., "meal_type": ..., "food_name": ...}

# 변경 후 — list[dict] 반환, 다중 끼니 지원
async def parse_meal_input(raw_text: str) -> list[dict]:
    prompt = (
        "... 끼니가 여러 개이면 각각 추출해줘.\n"
        '{"meals": [{"days_ago": 숫자, "meal_type": "...", "food_name": "..."}, ...]}'
    )
    data = json.loads(resp.choices[0].message.content)
    meals = data.get("meals", [])
    # fallback: dict 반환 시 list로 감쌈
    if isinstance(meals, dict):
        meals = [meals]
    return result  # list[dict]
```

**GPT 프롬프트 규칙 변경:**
- `food_name`: "음식명만 깔끔하게 추출 (조사/어미 제거)" → "음식명과 수량을 함께 추출 (조사/어미만 제거, 수량은 유지)"
- `max_tokens`: 60 → 300
- 응답 형식: 단일 JSON 객체 → `{"meals": [...]}` 래퍼

**효과:** "아침 치킨, 점심 샌드위치 2개" 동시 입력 시 두 끼니 모두 인식 및 저장됨. 수량(2개)도 food_name에 보존됨.

---

## 7. `cogs/meal.py` + `utils/embed.py` — 식사 기록 쓰레드 텍스트 무시 수정

### 문제

`on_message`에 `if not message.attachments: return` 가드가 있어, 유저가 식사 쓰레드에 직접 채팅 입력 시 아무 반응이 없었음.

### 변경 내용 — `cogs/meal.py`

**`on_message` 재구조화:**
```python
# 기존
if not message.attachments:
    return   # ← 텍스트 입력 전부 차단

# 변경 후
image_attachments = [a for a in message.attachments if a.content_type.startswith("image/")]
if image_attachments:
    # 사진 처리 (기존 로직)
    ...
    return

# 텍스트 입력 처리 (신규)
if message.content.strip() and not message.content.strip().startswith(('/', '!')):
    await _process_text_meal(message, user_id, user)
```

**신규 함수 `_process_text_meal(message, user_id, user)` 추가:**
- `parse_meal_input(raw_text)` 단일 호출 → `list[dict]` 순회
- 끼니별 칼로리 분석(`search_food_nutrition` → GPT fallback), DB 저장
- 타마고치 수치 통합 갱신 (오늘 끼니만)
- 결과 메시지 일괄 출력

**`MealInputModal.on_submit` 다중 끼니 처리로 교체 (`utils/embed.py`):**
```python
# 기존 — 단일 끼니만 처리
parsed    = await parse_meal_input(raw_text)   # dict
days_ago  = parsed.get("days_ago", 0)
...단일 저장 및 응답...

# 변경 후 — 다중 끼니 루프
parsed_meals = await parse_meal_input(raw_text)   # list[dict]
results = []
for parsed in parsed_meals:
    ...끼니별 저장 및 results 누적...
단일 타마고치 업데이트, 단일 followup 응답
```

**효과:** 식사 쓰레드에 직접 채팅으로 "아침 치킨, 점심 샌드위치" 입력 시 두 끼니 모두 인식 및 저장됨.

---

## 8. `utils/thread_helper.py` (신규) + 각 봇 파일 — 전용 쓰레드 자동 join 미동작 수정

### 문제

식사/날씨/메일/체중 봇이 서버에 초대되어 있어도 각 유저의 전용 쓰레드에 join하지 않아, `on_message` 이벤트를 수신하지 못했음.

### 변경 내용

**`utils/thread_helper.py` 신규 생성:**
```python
async def join_assigned_threads(bot, thread_field: str):
    """봇 시작 시 DB에서 담당 쓰레드 ID를 읽어 모두 join."""
    for user_data in get_all_users():
        tid = user_data.get(thread_field)
        ...guild.get_thread(tid) 또는 fetch_channel(tid)...
        await t.join()

async def join_if_mine(bot, thread: discord.Thread, thread_field: str):
    """신규 쓰레드 생성 시 담당 쓰레드이면 join."""
    for user_data in get_all_users():
        if str(user_data.get(thread_field, "")) == str(thread.id):
            await thread.join()
            return
```

**각 봇 파일 4개 (`bot_meal.py`, `bot_weather.py`, `bot_mail.py`, `bot_weight.py`) 동일 패턴 추가:**
```python
from utils.thread_helper import join_assigned_threads, join_if_mine

@bot.event
async def on_thread_create(thread):
    await join_if_mine(bot, thread, "meal_thread_id")  # 봇별 field 사용

@bot.event
async def on_ready():
    ...
    await join_assigned_threads(bot, "meal_thread_id")
```

**효과:** 봇 재시작 시 기존 쓰레드 자동 join, 신규 쓰레드 생성 시에도 즉시 join하여 on_message 이벤트 정상 수신.

---

## 변경 파일 요약 (세션 2)

| 파일 | 변경 | 주요 변경 |
|------|------|-----------|
| `utils/gpt.py` | 수정 | `parse_meal_input` → `list[dict]`, 다중 끼니 + 수량 보존 |
| `cogs/meal.py` | 수정 | `import re` 제거, `_process_text_meal` 신규, `on_message` 재구조화 |
| `utils/embed.py` | 수정 | `import re` 제거, `MealInputModal.on_submit` 다중 끼니 루프 |
| `utils/thread_helper.py` | 신규 | `join_assigned_threads`, `join_if_mine` 공용 헬퍼 |
| `bot_meal.py` | 수정 | `on_ready` + `on_thread_create` 쓰레드 join 추가 |
| `bot_weather.py` | 수정 | 동일 |
| `bot_mail.py` | 수정 | 동일 |
| `bot_weight.py` | 수정 | 동일 |
