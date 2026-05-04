# 식사봇 (bot_meal.py) 제작 로드맵

> last_updated: 2026-04-13 | 현재 버전: v3.2 ✅ 운영 중

---

## 현재 상태 요약

### 구현 완료

- `bot_meal.py`: `cogs.meal` 단독 로드, `DISCORD_TOKEN_MEAL` 사용
- `cogs/meal.py`: `on_message` 감지 → 사진 식사 분석 → DB 저장
- 60초 대기 상태: `users.meal_waiting_until` (DB 기반, cross-process 공유)
- GPT-4o Vision 분석 → `utils/nutrition.py` 영양소 조회 → ML 보정
- `_build_analysis_embed()` 헬퍼로 분석 결과 Embed 생성

### 처리 흐름

```
[먹구름봇] 📸 버튼 클릭
  → set_meal_waiting(user_id, 60s)    [DB 기록]
  → "식사 쓰레드에 사진을 올려주세요" 안내

[식사봇] on_message (모든 메시지 감지)
  → attachment 있는 메시지인가?
  → meal_thread_id 또는 thread_id 에 올라온 사진인가?
  → is_meal_waiting(user_id)?          [DB 조회]
  → GPT-4o Vision 분석
  → clear_meal_waiting(user_id)        [DB 초기화]
  → 분석 결과 Embed → 확인 버튼 → DB 저장
```

---

## Phase 1 — 안정화 작업 (v3.2.x)

### 1-1. 대기 만료 안내 메시지

현재 60초 대기가 만료되면 사진을 올려도 조용히 무시됨.  
→ 만료 감지 시 유저에게 안내 필요.

```python
# cogs/meal.py on_message() 수정

waiting_until = user.get("meal_waiting_until")
if waiting_until and datetime.utcnow() > waiting_until:
    # 대기 만료 → 안내 후 종료
    await message.channel.send(
        f"<@{message.author.id}> 사진 입력 시간이 초과됐어요.\n"
        "다시 📸 버튼을 눌러주세요!",
        delete_after=10
    )
    return
```

### 1-2. 다중 사진 처리

현재 메시지 당 첫 번째 attachment만 처리.  
→ 복수 사진 첨부 시 각각 분석 or 합산 처리.

```python
# 옵션 A: 첫 번째만 분석 (현재) — 유지 가능
# 옵션 B: 모든 attachment 순서대로 분석
for attachment in message.attachments[:3]:  # 최대 3장
    if attachment.content_type.startswith("image/"):
        result = await analyze_photo(attachment.url, meal_type)
        meals.append(result)
```

### 1-3. 분석 실패 처리 개선

GPT-4o Vision이 "식사가 아닌 이미지"로 판단한 경우 현재 아무 응답 없음.  
→ 명시적 안내 메시지 추가.

```python
if not result or result.get("calories", 0) == 0:
    await message.channel.send(
        "식사 사진을 인식하지 못했어요. 음식이 잘 보이는 사진으로 다시 시도해주세요.",
        delete_after=15
    )
    return
```

---

## Phase 2 — 직접 업로드 경로 개선 (v3.3)

> 버튼 없이 식사 쓰레드에 바로 사진 올려도 감지되는 경로

현재 "직접 업로드"는 `is_meal_waiting` 우회로 이미 동작하나, 확인 UX가 불명확.

### 2-1. 직접 업로드 시 끼니 선택 UI 추가

버튼 경로: 먹구름봇에서 끼니를 먼저 선택 → 사진 업로드  
직접 경로: 사진만 올림 → 끼니 선택 UI 없음 → 기본값 `식사`로 저장됨

```python
# cogs/meal.py — 직접 업로드 감지 시
# meal_waiting_until이 없는 경우 → 끼니 선택 Select 먼저 표시

class MealTypeSelectView(discord.ui.View):
    @discord.ui.select(
        placeholder="끼니를 선택해주세요",
        options=[
            discord.SelectOption(label="아침", value="아침"),
            discord.SelectOption(label="점심", value="점심"),
            discord.SelectOption(label="저녁", value="저녁"),
            discord.SelectOption(label="간식", value="간식"),
        ]
    )
    async def select_callback(self, interaction, select):
        # 선택 후 분석 진행
        await analyze_and_save(interaction, attachment_url, select.values[0])
```

---

## Phase 3 — n8n 음식 추천 연동 (v3.4)

> 식사봇에서 `뭐 먹을까?` 버튼 → 오늘 식사 기반 추천

### 3-1. 분석 결과 Embed에 추천 버튼 추가

```python
# _build_analysis_embed() 반환 View에 버튼 추가
class MealAnalysisView(discord.ui.View):
    @discord.ui.button(label="🍜 이번엔 뭐 먹을까?", style=discord.ButtonStyle.secondary)
    async def recommend_callback(self, interaction, button):
        # n8n POST → 추천 결과 ephemeral
        ...
```

---

## Phase 4 — ML 강화 (v3.5+)

### 4-1. 사진 기반 학습 데이터 확보

현재 ML 학습 데이터는 텍스트 입력 기반.  
사진 입력 기록(`input_method = 'photo'`)이 30개 이상 누적되면 별도 모델 학습.

```python
# utils/ml.py _load_training_data() 수정
# input_method 필터링으로 모델 분리 가능
photo_meals = [m for m in meals if m["input_method"] == "photo"]
text_meals  = [m for m in meals if m["input_method"] == "text"]
```

### 4-2. 반찬 항목별 DB 누적

현재 GPT Vision은 "비빔밥 1인분" 같은 통합 라벨 반환.  
반찬별 분해 → 영양소 DB 매핑 → 더 정확한 칼로리 (장기 목표).

---

## 주요 파일 위치

| 파일 | 역할 |
|------|------|
| `bot_meal.py` | 봇 진입점, `cogs.meal` 로드 |
| `cogs/meal.py` | `on_message` 핸들러, 분석 로직 |
| `utils/db.py` | `is_meal_waiting()`, `set_meal_waiting()`, `clear_meal_waiting()`, `create_meal()` |
| `utils/gpt.py` | `analyze_meal_text()` (Vision API) |
| `utils/nutrition.py` | 식약처 API 조회, GPT fallback |
| `utils/ml.py` | 칼로리 보정 모델 |

---

## 설계 원칙 (변경 금지)

1. 사진 대기 상태는 반드시 DB (`meal_waiting_until`) 기반 — in-memory 금지
2. `meal_thread_id or thread_id` fallback 항상 유지
3. 칼로리 0 저장 차단 — 분석 실패 시 저장하지 않음
4. 중복 제출 방지: `_meal_submitting` 집합으로 동일 메시지 2회 처리 차단
