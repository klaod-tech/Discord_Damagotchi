# 일기봇 — 일기 입력 흐름

---

## 1. `/일기` 커맨드 흐름

```
유저: /일기
  → DiaryCog.diary_cmd()
  → send_modal(DiaryInputModal)

유저: 일기 작성 (최대 1000자)
  → DiaryInputModal.on_submit()
  → defer(ephemeral=True, thinking=True)
  → analyze_emotion(text)
      → GPT-4o: emotion_tag, emotion_score, comment
  → save_diary(user_id, text, emotion_tag, emotion_score, comment)
  → 감정 이모지/색상 결정
  → Embed 구성:
       title: "{emoji} 오늘의 일기 기록 완료"
       description: *{comment}*
       📝 일기: text[:200] + "..." (200자 초과 시)
       🎭 감정: {emoji} {emotion_tag} (강도: {int(score*100)}%)
       footer: "오늘도 수고했어 🌙"
  → thread_id = diary_thread_id or thread_id
  → thread.send(embed=embed)  ← 일기 전용 쓰레드에 공개 전송
  → followup.send("✅ 일기가 기록됐어!", ephemeral=True)
```

---

## 2. `/감정통계` 커맨드 흐름

```
유저: /감정통계
  → DiaryCog.emotion_stats_cmd()
  → get_emotion_stats(user_id, days=7)
  → Embed 구성:
       title: "🎭 최근 7일 감정 분포"
       fields:
         - 기쁨 😊: N회
         - 슬픔 😢: N회
         - ...
       description: "가장 많은 감정: {top_emotion}"
  → send(embed, ephemeral=True)
```

---

## 3. GPT 감정 분석 상세

```python
analyze_emotion(text: str) -> dict

# 반환:
{
    "emotion_tag":   str,   # 기쁨/슬픔/화남/평온/불안/설렘
    "emotion_score": float, # 0.0 ~ 1.0 (감정 강도)
    "comment":       str,   # 다마고치 반응 대사 (2문장 이내)
}

# 모델: gpt-4o, max_tokens=200
# JSON만 반환, 펜스 제거 처리 포함
```

---

## 4. 감정 태그 → 색상/이모지

```python
emotion_emoji = {
    "기쁨": "😊", "슬픔": "😢", "화남": "😤",
    "평온": "😌", "불안": "😰", "설렘": "🥰",
}

def _emotion_color(emotion_tag: str) -> int:
    return {
        "기쁨": 0xFFD700,
        "슬픔": 0x4169E1,
        "화남": 0xFF4500,
        "평온": 0x90EE90,
        "불안": 0xFFA500,
        "설렘": 0xFF69B4,
    }.get(emotion_tag, 0x808080)
```
