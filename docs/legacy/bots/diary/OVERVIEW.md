# 일기봇 — 오버뷰

> 현재 상태: 📋 구상 단계 — UX 흐름 미결, 코드 없음  
> 구현 전 UX 기획 구체화 필요 (진입 방식, 채널 내 역할 등)

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot_diary.py` |
| 토큰 환경변수 | `DISCORD_TOKEN_DIARY` |
| 커맨드 prefix | `!diary_` |
| 담당 Cog | `cogs/diary.py` → `DiaryCog` (신규 생성) |
| 응답 위치 | `users.personal_channel_id` (직접 응답), Push 리포트 → `info_thread_id` |
| 담당 DB 테이블 | `diary_log` (신규 생성 필요) |
| 슬래시 커맨드 | `/일기`, `/감정통계` |

---

## 2. 역할 및 범위

### 이 봇이 하는 것
- `/일기` 슬래시 커맨드 → DiaryInputModal → GPT 감정 분석 + DB 저장
- 일기 전용 쓰레드에 감정 분석 Embed 전송
- `/감정통계` → 최근 7일 감정 분포 Embed

### 이 봇이 하지 않는 것
- 일기 입력 버튼 — v4.0 자연어 방식으로 대체 (버튼 없음)
- 식사 × 감정 상관 분석 — ML.md 참조

---

## 3. 설계 원칙

1. **비침습적** — 일기는 강제하지 않음, 버튼/커맨드로만 유도
2. **공감 우선** — GPT 응답은 분석보다 공감에 집중 (2문장 이내)
3. **프라이버시** — 일기 내용은 전용 쓰레드(ephemeral 아님)에 기록

---

## 4. 감정 태그 목록

| 태그 | 이모지 | 색상 |
|------|--------|------|
| 기쁨 | 😊 | 금색 `#FFD700` |
| 슬픔 | 😢 | 파란색 `#4169E1` |
| 화남 | 😤 | 빨간색 `#FF4500` |
| 평온 | 😌 | 연두색 `#90EE90` |
| 불안 | 😰 | 주황색 `#FFA500` |
| 설렘 | 🥰 | 핑크 `#FF69B4` |

---

## 5. 파일 구조 (구현 후)

```
bot_diary.py           ← 봇 진입점
cogs/diary.py          ← DiaryCog, DiaryInputModal, analyze_emotion()
utils/db.py            ← diary_log 테이블 + DB 함수 (마이그레이션 추가 필요)
```

---

## 6. 신규 구현 필요 항목 체크리스트

- [ ] `utils/db.py` — `diary_log` 테이블 마이그레이션 추가
- [ ] `utils/db.py` — `personal_channel_id`, `info_thread_id` 컬럼은 v4.0 온보딩에서 이미 추가됨 (별도 불필요)
- [ ] `utils/db.py` — DB 함수 5개 추가
- [ ] `cogs/onboarding.py` — 일기 전용 쓰레드 생성 추가
- [ ] `cogs/diary.py` — 신규 생성
- [ ] `bot_diary.py` — `cogs.diary` 로드 활성화
