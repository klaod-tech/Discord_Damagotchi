# 식사봇 — 오버뷰

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_meal.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_MEAL` |
| 커맨드 prefix | `!meal_` |
| 담당 Cog | `cogs/meal.py` → `MealPhotoCog` |
| 담당 쓰레드 | `users.meal_thread_id` |
| 담당 DB 테이블 | `meals` (소유) |
| 현재 상태 | ✅ cog 구현 완료 |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- 유저 전용 쓰레드(meal_thread_id)에서 이미지 첨부 감지
- `is_meal_waiting()` → True: 바로 GPT-4o Vision 분석 (사진 입력 대기 흐름)
- `is_meal_waiting()` → False: "📸 음식 사진이에요?" 감지 버튼 표시 (자발적 업로드 흐름)
- `MealPhotoDetectView`: [✅ 분석하기] / [❌ 아니야] 버튼
- `MealPhotoConfirmView`: 분석 결과 확인 + [✅ 기록하기] / [❌ 취소] 버튼
- DB 저장 후 먹구름봇 메인 Embed 갱신 (create_or_update_embed)

### 이 봇이 하지 않는 것
- 텍스트 식사 입력 → 먹구름봇 MealInputModal (utils/embed.py) 담당
- 식사 알림 스케줄러 → 먹구름봇 SchedulerCog 담당
- 사진 입력 버튼 UI → 먹구름봇 MealInputSelectView (utils/embed.py) 담당

---

## 3. 파일 구조

```
bot_meal.py          ← 봇 진입점 (DISCORD_TOKEN_MEAL)
cogs/meal.py         ← MealPhotoCog (on_message, 사진 분석, 확인 버튼)
utils/embed.py       ← MealInputModal (텍스트 입력, 먹구름봇 버튼에서 호출)
utils/db.py          ← is_meal_waiting, clear_meal_waiting, create_meal
utils/gpt_ml_bridge.py ← get_corrected_calories (ML 보정)
```

---

## 4. on_message 처리 조건

사진이 전송되어 on_message가 트리거되었을 때 처리하는 경우:

1. `message.author.bot` → 무시
2. 첨부파일 없음 → 무시
3. 이미지 아닌 첨부파일 → 무시
4. 채널이 discord.Thread 아님 → 무시
5. `get_user(user_id)` → None → 무시
6. `allowed_thread_id = user.get("meal_thread_id") or user.get("thread_id")`
   → 현재 쓰레드 ID와 다름 → 무시

위 6개 통과 시:
- `is_meal_waiting(user_id)` → True: 즉시 분석 (대기 흐름)
- False: 감지 버튼 표시 (자발적 업로드 흐름)

---

## 5. 중요 주의사항

- `import time`은 현재 cogs/meal.py에 유지 중 — 향후 **과거 식사 감지** 로직 구현 예정
  - 현재 시간 기준 당일/전날 판단 → 식사 과정 Embed 표시 여부 결정
- `input_method`: 텍스트 입력 = `"text"`, 사진 입력 = `"photo"` (배지 `photo_10` 조건)
- `MealPhotoConfirmView(timeout=180)` — 3분 후 버튼 자동 비활성화
- `MealPhotoDetectView(timeout=120)` — 2분 후 버튼 자동 비활성화
