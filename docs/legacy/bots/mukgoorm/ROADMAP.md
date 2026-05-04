# 먹구름봇 (bot.py) 제작 로드맵

> last_updated: 2026-04-13 | 현재 버전: v3.2 ✅ 운영 중

---

## 현재 상태 요약

### 로드된 Cogs

| Cog | 역할 | 상태 |
|-----|------|------|
| `cogs.onboarding` | 온보딩 Modal → 쓰레드 5개 생성 | ✅ |
| `cogs.summary` | 오늘 요약 Ephemeral | ✅ |
| `cogs.settings` | 설정 서브뷰 (내정보/위치/시간/이메일) | ✅ |
| `cogs.time_settings` | 10분 단위 시간 Select Menu | ✅ |
| `cogs.scheduler` | 22:00 판정, 식사 알림, 주간 리포트, ML 재학습 | ✅ |
| `cogs.weight` | 체중 입력 Modal (임시 — Phase 1에서 분리 예정) | 🔄 |

### 담당하지 않는 기능 (분리 완료)

- 사진 식사 입력 → `bot_meal.py`
- 날씨 알림 → `bot_weather.py`
- 이메일 모니터링 → `bot_mail.py`

---

## Phase 1 — 체중 Cog 분리 (v3.3 작업)

> `cogs.weight`를 `bot_weight.py`로 이전하고 bot.py에서 제거

### 1-1. bot.py COGS 목록 수정

```python
# bot.py
COGS = [
    "cogs.onboarding",
    "cogs.summary",
    "cogs.settings",
    "cogs.time_settings",
    "cogs.scheduler",
    # "cogs.weight",  ← 제거 (bot_weight.py로 이전)
]
```

### 1-2. embed.py weight_button 처리

`WeightInputModal`은 `utils/embed.py`의 weight_button 콜백에서 직접 사용.  
Cog 없이도 Modal 자체는 동작 → `from cogs.weight import WeightInputModal` import만 유지.

```python
# utils/embed.py — 변경 없음 (WeightInputModal import 유지)
from cogs.weight import WeightInputModal
```

### 1-3. 슬래시 커맨드 충돌 방지

- `WeightCog`는 bot_weight.py에서만 로드
- bot.py에서 `cogs.weight` 언로드 후 반드시 `/체중기록` 커맨드가 bot_weight.py에서 등록되는지 확인

---

## Phase 2 — 버그 수정 (v3.2.x)

### 2-1. 여러 끼니 동시 입력 파싱

```python
# utils/embed.py MealInputModal.on_submit() 수정 대상
# 현재: 전체 입력을 하나의 식사로 파싱
# 목표: 쉼표(,) 또는 줄바꿈으로 구분 → 각각 parse_meal_input() 호출

inputs = re.split(r'[,\n]', raw_text)
for item in inputs:
    meal = await parse_meal_input(item.strip(), meal_type)
    if meal: await save_and_respond(meal)
```

### 2-2. gpt_ml_bridge 파라미터 수정

```python
# utils/gpt_ml_bridge.py:73
# 현재 시그니처:
async def generate_comment_with_pattern(user_id, tamagotchi, recent_meals)
# 실제 호출부가 기대하는 시그니처 확인 후 수정
```

### 2-3. 식약처 검색어 전처리

```python
# utils/nutrition.py search_food_nutrition() 진입부 추가
import re
query = re.sub(r'[\d]+\s*(g|ml|개|인분|조각)', '', query).strip()
```

---

## Phase 3 — n8n 음식 추천 연동 (v3.3)

> `🍜 뭐 먹고 싶어?` 버튼 활성화

### 3-1. 버튼 비활성화 → 활성화

```python
# utils/embed.py MainView 내 food_btn
# 현재: disabled=True, label="🍜 뭐 먹고 싶어? (준비 중)"
# 변경: disabled=False 조건 → N8N_FOOD_WEBHOOK_URL 환경변수 존재 시 활성화

import os
N8N_URL = os.getenv("N8N_FOOD_WEBHOOK_URL")
food_btn.disabled = not bool(N8N_URL)
```

### 3-2. 웹훅 POST 구현

```python
# utils/embed.py food_button callback
async def food_button_callback(self, interaction, button):
    user = get_user(interaction.user.id)
    today_meals = get_meals_by_date(user["user_id"], date.today())

    payload = {
        "user_id": str(user["user_id"]),
        "location": {"city": user["city"]},
        "remaining_calories": user["daily_cal_target"] - sum(m["calories"] for m in today_meals),
        "daily_cal_target": user["daily_cal_target"],
        "today_meals": [m["food_name"] for m in today_meals],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(N8N_URL, json=payload) as resp:
            data = await resp.json()
    
    # data 포맷은 n8n 팀원 확정 후 embed 구성
    await interaction.response.send_message(embed=build_recommend_embed(data), ephemeral=True)
```

### 3-3. 위치 주소 상세화 (옵션)

날씨용 `city` 필드와 분리하여 음식 추천 전용 `address` 컬럼 추가 고려:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;
-- 예: "마포구 합정동"
```

설정 Modal에 주소 입력 필드 추가:
```python
# cogs/settings.py SettingsSubView → 위치 설정 Modal에 address 필드 추가
```

---

## Phase 3.5 — 채널 구조 전환 (v4.0 사전 작업)

> 유저별 전용 채널 생성 방식으로 온보딩 전환

### 3.5-1. 온보딩 수정 (cogs/onboarding.py)

```python
# 기존: #다마고치 채널에 쓰레드 생성
# 변경: "먹구름" 카테고리에 전용 채널 생성

category = guild.get_channel(int(os.getenv("TAMAGOTCHI_CATEGORY_ID")))

# 유저 전용 채널 생성
personal_channel = await guild.create_text_channel(
    name=f"{name}-채팅창",
    category=category,
    overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
)
set_personal_channel_id(user_id, str(personal_channel.id))

# 전용 채널 안에 기능봇 쓰레드 생성
meal_thread = await personal_channel.create_thread(name=f"🍽️ {name}의 식사기록", ...)
# ... 나머지 쓰레드들
```

### 3.5-2. 환경변수 추가

```bash
TAMAGOTCHI_CATEGORY_ID  # "먹구름" 카테고리 ID
```

### 3.5-3. DB 컬럼 추가

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS personal_channel_id TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;
```

### 3.5-4. 온보딩 모달 필드 추가

```python
# cogs/onboarding.py OnboardingModal
address = discord.ui.TextInput(
    label="동네 주소 (음식 추천용)",
    placeholder="예: 마포구 합정동 (선택 입력)",
    required=False,
    max_length=50
)
```

---

## Phase 4 — 오케스트레이터 전환 (v4.0)

> bot.py가 메시지를 GPT/ML로 파싱 → 관련 봇 자동 트리거

### 4-1. task_queue 테이블 생성

```sql
CREATE TABLE IF NOT EXISTS task_queue (
  task_id     SERIAL PRIMARY KEY,
  bot_target  TEXT NOT NULL,    -- 'meal' | 'diary' | 'schedule' | 'weight'
  user_id     TEXT NOT NULL,
  payload     TEXT,             -- JSON
  status      TEXT DEFAULT 'pending',  -- pending | processing | done
  created_at  TIMESTAMP DEFAULT NOW()
);
```

### 4-2. 오케스트레이터 on_message 구현

```python
# bot.py — on_message 이벤트
@bot.event
async def on_message(message):
    if message.author.bot: return
    user = get_user(str(message.author.id))
    if not user: return

    # GPT 의도 분석
    intents = await parse_intents(message.content)
    # 예: {"meal": True, "diary": True, "schedule": False, "weather": False}

    for bot_target, triggered in intents.items():
        if triggered:
            insert_task_queue(bot_target, user["user_id"], message.content)
```

### 4-3. 전문봇별 태스크 큐 폴링

```python
# 각 전문봇 (bot_meal.py, bot_diary.py 등)
# APScheduler 30초 주기로 task_queue 폴링
@scheduler.scheduled_job('interval', seconds=30)
async def poll_task_queue():
    tasks = get_pending_tasks(bot_target='meal')
    for task in tasks:
        await process_task(task)
        mark_task_done(task['task_id'])
```

### 4-4. GPT 의도 파싱 프롬프트 (1단계)

```python
INTENT_PROMPT = """
다음 메시지에서 각 의도가 있는지 true/false로 답하세요. JSON만 반환.
{"meal": bool, "diary": bool, "schedule": bool, "weight": bool, "none": bool}

메시지: {text}
"""
```

### 4-5. intent_log 테이블 생성 (학습 데이터 수집)

```sql
CREATE TABLE IF NOT EXISTS intent_log (
  log_id         SERIAL PRIMARY KEY,
  user_id        TEXT NOT NULL,
  message        TEXT NOT NULL,       -- 유저 발화 원문
  intent         TEXT NOT NULL,       -- meal | diary | schedule | weight | none
  entity_json    TEXT,                -- {"food": "비빔밥", "meal_type": "점심"}
  classified_by  TEXT DEFAULT 'gpt',  -- 'gpt' | 'ml'
  created_at     TIMESTAMP DEFAULT NOW()
);
```

---

## Phase 5 — ML 의도 분류기 전환 (v4.0 이후)

> GPT가 누적한 intent_log 데이터로 ML 의도 분류기 학습 → GPT 대체

### 5-1. 의도 분류기 (utils/intent_classifier.py 신규)

```python
# utils/intent_classifier.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import pickle

class IntentClassifier:
    """
    유저별 의도 분류기.
    GPT가 레이블링한 intent_log 데이터로 학습.
    활성화 조건: 유저당 50건+ 누적
    """

    def train(self, user_id: str, messages: list, labels: list):
        vec = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
        X = vec.fit_transform(messages)
        clf = LogisticRegression(max_iter=200)
        clf.fit(X, labels)
        with open(f"models/intent_{user_id}.pkl", "wb") as f:
            pickle.dump((vec, clf), f)

    def predict(self, user_id: str, text: str) -> str:
        """
        반환: meal | diary | schedule | weight | none
        모델 없으면 None 반환 → GPT fallback
        """
        try:
            with open(f"models/intent_{user_id}.pkl", "rb") as f:
                vec, clf = pickle.load(f)
            return clf.predict(vec.transform([text]))[0]
        except FileNotFoundError:
            return None  # GPT fallback
```

### 5-2. 의도 분류기 재학습 스케줄러

```python
# cogs/scheduler.py — 매주 일요일 03:30
@scheduler.scheduled_job('cron', day_of_week='sun', hour=3, minute=30)
async def _weekly_intent_retrain():
    """유저별 intent_log 50건+ 이면 ML 재학습"""
    users = get_all_users()
    for user in users:
        logs = get_intent_logs(user["user_id"], min_count=50)
        if len(logs) >= 50:
            classifier.train(
                user["user_id"],
                [l["message"] for l in logs],
                [l["intent"] for l in logs]
            )
```

### 5-3. GPT → ML 전환 흐름

```
[봇 on_message]
  1. ML 분류기 predict() 시도 (모델 없으면 None)
  2. None → GPT로 의도 분류 + intent_log 저장 (학습 데이터 누적)
  3. 분류 결과 → task_queue 삽입 → 전문봇 처리
  4. 50건+ 누적 → 매주 일요일 ML 재학습
  5. ML 분류기 완성 후 → GPT 호출 생략, 엔티티 추출만 GPT 사용
```

---

## 스케줄러 현황 (cogs/scheduler.py)

| 작업 | 시간 | 주기 |
|------|------|------|
| 칼로리 판정 + 스트릭/배지 | 22:00 KST | 매일 |
| 식사 알림 (1차) | 식사시간 -10분 | 매일 |
| 식사 알림 (2차) | 식사시간 +30분 | 매일 |
| 식사 알림 (3차) | 식사시간 +90분 | 매일 |
| hunger 감소 | 매시 정각 | 매시간 |
| ML 재학습 | 03:00 | 매주 일요일 |
| 주간 리포트 | 08:00 | 매주 일요일 |

---

## 설계 원칙 (변경 금지)

1. HP/Hunger/Mood 수치는 절대 유저에게 직접 노출하지 않음
2. 칼로리/영양소는 `/오늘요약` ephemeral에서만 표시
3. 먹구름봇은 v4.0 이전까지 식사 텍스트 입력 포함 유지
4. 기존 유저는 신규 쓰레드 ID가 NULL → `thread_id` fallback 보장
