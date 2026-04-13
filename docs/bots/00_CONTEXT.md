# 먹구름 멀티봇 개발 가이드 — 인덱스

> **이 폴더의 목적**: 각 봇을 독립적인 Claude 세션에서 개발할 수 있도록 문서를 분리.  
> 각 봇 MD는 해당 봇만 개발하기 위한 **완전 자급적 문서**입니다.

---

## 공통 문서 (모든 봇 개발자가 먼저 읽어야 함)

| 파일 | 내용 |
|------|------|
| [`01_ARCHITECTURE.md`](01_ARCHITECTURE.md) | 전체 봇 구조, 봇 간 통신 방식, 소유권 규칙, 충돌 방지 |
| [`02_SHARED_DB.md`](02_SHARED_DB.md) | DB 스키마 전체, 공통 함수, 마이그레이션 규칙 |
| [`03_SHARED_UTILS.md`](03_SHARED_UTILS.md) | 공통 유틸리티 (gpt.py / embed.py / image.py / ml.py 등) |

---

## 봇별 개발 문서

| 봇 | 파일 | 상태 | 담당 쓰레드 |
|----|------|------|------------|
| 식사봇 | [`BOT_MEAL.md`](BOT_MEAL.md) | ✅ cog 구현 완료 | `meal_thread_id` |
| 날씨봇 | [`BOT_WEATHER.md`](BOT_WEATHER.md) | ✅ cog 구현 완료 | `weather_thread_id` |
| 체중관리봇 | [`BOT_WEIGHT.md`](BOT_WEIGHT.md) | 🔄 버튼만 구현 (이전 예정) | `weight_thread_id` |
| 이메일봇 | [`BOT_EMAIL.md`](BOT_EMAIL.md) | ✅ 완전 구현 | `mail_thread_id` |
| 일기봇 | [`BOT_DIARY.md`](BOT_DIARY.md) | 📋 설계 완료, 구현 예정 | `diary_thread_id` |
| 일정봇 | [`BOT_SCHEDULE.md`](BOT_SCHEDULE.md) | 📋 설계 완료, 구현 예정 | `schedule_thread_id` |

---

## Claude 세션 시작 가이드

각 봇을 새 Claude 세션에서 개발할 때 다음 순서로 파일을 제공하세요:

```
1. 01_ARCHITECTURE.md   ← 전체 구조 파악
2. 02_SHARED_DB.md      ← DB 함수 규칙
3. 03_SHARED_UTILS.md   ← 공통 유틸 파악
4. BOT_XXX.md           ← 해당 봇 전용 구현 스펙
```

---

## 핵심 충돌 방지 원칙

| 원칙 | 내용 |
|------|------|
| **테이블 소유권** | 각 봇은 자신이 소유한 테이블에만 INSERT/UPDATE |
| **users 테이블** | 공유 읽기 가능, 컬럼 추가 시 `ADD COLUMN IF NOT EXISTS` 필수 |
| **thread_id** | `new_thread_id or thread_id` 패턴으로 fallback 유지 |
| **명령어 충돌** | 봇마다 prefix 다름 (`!meal_`, `!weather_`, `!weight_` 등) |
| **슬래시 커맨드** | 봇별로 네임스페이스 분리 (e.g. `/meal_input`, `/weather_now`) |
