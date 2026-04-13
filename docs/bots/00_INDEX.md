# 먹구름 멀티봇 개발 가이드 — 마스터 인덱스

> **버전**: v3.2 | **최종 수정**: 2026-04-13  
> 각 봇을 독립적인 Claude 세션에서 개발할 수 있도록 봇별 하위 폴더로 구성됩니다.

---

## 폴더 구조

```
docs/bots/
├── 00_INDEX.md              ← 이 파일
├── shared/                  ← 모든 봇 공통 (먼저 읽기)
│   ├── ARCHITECTURE.md      전체 봇 구조, 소유권, 충돌 방지 규칙
│   ├── DB.md                DB 스키마 전체 + 공통 함수
│   └── UTILS.md             공통 유틸리티 사용법
├── mukgoorm/                ← 먹구름봇 (오케스트레이터)
│   ├── OVERVIEW.md          역할, Cog 목록, 버튼 구조
│   ├── FLOWS.md             온보딩, 식사입력, 하루정리, 설정 흐름
│   └── SCHEDULER.md         APScheduler 전체 Job 목록 및 로직
├── meal/                    ← 식사봇
│   ├── OVERVIEW.md          역할, 현재 구현 상태, bot 파일
│   ├── FLOWS.md             사진 감지 흐름 (2경로), 봇 간 협력
│   ├── DB.md                meals 테이블, DB 함수 목록
│   └── ML.md                칼로리 보정 ML 현황 및 계획
├── weather/                 ← 날씨봇
│   ├── OVERVIEW.md          역할, 스케줄러 구조
│   ├── FLOWS.md             날씨 알림 흐름, 스케줄러 동작
│   └── API.md               기상청/에어코리아 API 상세
├── weight/                  ← 체중관리봇
│   ├── OVERVIEW.md          역할, 현재 상태 (skeleton)
│   ├── FLOWS.md             체중 기록 흐름, 프로그레스 바
│   ├── DB.md                weight_log 테이블
│   └── ROADMAP.md           봇 이전 절차, Phase별 구현 계획
├── email/                   ← 이메일봇
│   ├── OVERVIEW.md          역할, 슬래시 커맨드 목록
│   ├── FLOWS.md             IMAP 폴링 흐름, 스팸 필터 3단계
│   ├── DB.md                email_senders/email_log 테이블
│   └── ML.md                스팸 분류 ML 계획
├── diary/                   ← 일기봇 (구현 예정)
│   ├── OVERVIEW.md          역할, 설계 원칙
│   ├── FLOWS.md             일기 입력 흐름, 감정 분석
│   ├── DB.md                diary_log 테이블 + 신규 함수 코드
│   ├── IMPLEMENTATION.md    cogs/diary.py 전체 구현 코드
│   └── ML.md                감정 분석, 식사×감정 상관관계
└── schedule/                ← 일정봇 (구현 예정)
    ├── OVERVIEW.md          역할, 반복 일정 설계
    ├── FLOWS.md             일정 등록/알림/완료 흐름
    ├── DB.md                schedule_log 테이블 + 신규 함수 코드
    ├── IMPLEMENTATION.md    cogs/schedule.py 전체 구현 코드
    └── ML.md                반복 패턴 ML 계획
```

---

## Claude 세션 시작 방법

새 Claude 세션에서 특정 봇 개발 시 제공할 파일 순서:

```
1. shared/ARCHITECTURE.md   ← 전체 구조 파악
2. shared/DB.md             ← DB 함수 규칙
3. shared/UTILS.md          ← 공통 유틸 파악
4. {봇}/OVERVIEW.md         ← 봇 역할 파악
5. {봇}/FLOWS.md            ← 상세 흐름
6. {봇}/DB.md               ← DB 담당 범위
7. {봇}/IMPLEMENTATION.md   ← 코드 구현 (diary/schedule만 해당)
```

---

## 봇 상태 요약

| 봇 | 폴더 | 상태 | 토큰 |
|----|------|------|------|
| 먹구름봇 (오케스트레이터) | `mukgoorm/` | ✅ 운영 | `DISCORD_TOKEN` |
| 메일봇 | `email/` | ✅ 완전 구현 | `DISCORD_TOKEN_EMAIL` |
| 식사봇 | `meal/` | ✅ cog 구현 완료 | `DISCORD_TOKEN_MEAL` |
| 날씨봇 | `weather/` | ✅ cog 구현 완료 | `DISCORD_TOKEN_WEATHER` |
| 체중관리봇 | `weight/` | 🔄 이전 준비 완료 | `DISCORD_TOKEN_WEIGHT` |
| 일기봇 | `diary/` | 📋 설계 완료, 구현 예정 | `DISCORD_TOKEN_DIARY` |
| 일정봇 | `schedule/` | 📋 설계 완료, 구현 예정 | `DISCORD_TOKEN_SCHEDULE` |

---

## 핵심 설계 원칙 (절대 불변)

| # | 원칙 |
|---|------|
| 1 | `hp / hunger / mood` 수치 사용자에게 **절대 직접 노출 금지** |
| 2 | 날씨는 별도 알림 없음 — 기상 시간에 이미지 자동 교체로만 전달 |
| 3 | 칼로리/영양소 수치는 하루 정리 Ephemeral로만 확인 가능 |
| 4 | 이미지 파일명 소문자 고정 (`eat.png` O, `Eat.PNG` X) |
| 5 | 각 봇은 자신이 소유한 DB 테이블에만 INSERT/UPDATE |
| 6 | 기존 유저 fallback: `new_thread_id or thread_id` |
