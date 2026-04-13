# 먹구름봇 — 오버뷰

> **먹구름봇**은 멀티봇 시스템의 오케스트레이터.  
> 온보딩, 메인 Embed, 설정, 스케줄러를 담당하며 다른 봇들이 사용할 DB 컬럼·쓰레드를 온보딩 시 초기화한다.

---

## 1. 봇 기본 정보

| 항목 | 내용 |
|------|------|
| 봇 파일 | `bot.py` |
| 토큰 환경변수 | `DISCORD_TOKEN` |
| 커맨드 prefix | `!` |
| 슬래시 커맨드 | `/start` |

---

## 2. 로드하는 Cog 목록

```python
# bot.py main() 에서 로드 순서
"cogs.onboarding"     # /start 슬래시커맨드, OnboardingModal, StartView
"cogs.summary"        # 주간 리포트 (SummaryCog — 단독 cog, 별도 scheduler 아님)
"cogs.settings"       # 설정 SubView, EmailSubView
"cogs.time_settings"  # 기상/식사 시간 설정 모달
"cogs.scheduler"      # APScheduler 전체 Job 관리 (SchedulerCog)
"cogs.weight"         # 체중 기록 Modal + WeightInputModal (먹구름봇에서도 로드)
```

> 주의: `cogs.meal`과 `cogs.weather`는 먹구름봇에서 **로드하지 않음** — 각각 bot_meal.py, bot_weather.py에서 로드

---

## 3. 담당 기능 요약

### 온보딩 (`cogs/onboarding.py`)
- `/start` 슬래시 커맨드 → 채널에 시작 Embed + StartView 고정
- `StartView` "시작하기" 버튼 → `OnboardingModal` 열기
- 온보딩 완료 시 전용 쓰레드 **5개** 일괄 생성:
  - `{이름}의 {캐릭터명}` (메인)
  - `📧 {이름}의 메일함`
  - `🍽️ {이름}의 식사 기록`
  - `🌤️ {이름}의 날씨`
  - `⚖️ {이름}의 체중관리`
- GPT로 권장 칼로리 계산 후 DB 저장
- 온보딩 완료 후 시간 설정 (TimeStep1View) 자동 팝업

### 메인 Embed (`utils/embed.py`)
- `create_or_update_embed()`: 쓰레드에 다마고치 Embed 생성 또는 수정
- `embed_message_id` DB에 저장 → 재연결 후에도 기존 메시지 수정 (새 메시지 X)
- 버튼 Row 0: `🍽️ 식사 입력` / `📋 하루 정리` / `🍜 뭐 먹고 싶어?`
- 버튼 Row 1: `⚙️ 설정` / `⚖️ 체중 기록`
- `MainView(timeout=None)` — Persistent View (봇 재시작 후에도 동작)

### 설정 (`cogs/settings.py`, `cogs/time_settings.py`)
- `SettingsSubView`: 설정 항목 선택 (도시/체중목표/이메일)
- `EmailSubView`: 이메일 설정 진입점 (이메일봇의 슬래시커맨드와 동일 Modal 공유)
- 시간 설정: `TimeStep1View` (기상시간) → `TimeStep2View` (아침) → `TimeStep3View` (점심) → `TimeStep4View` (저녁)
- 시간 설정 완료 시 `SchedulerCog.register_meal_jobs()` 자동 호출

### 스케줄러 (`cogs/scheduler.py`)
→ 상세 내용은 `mukgoorm/SCHEDULER.md` 참조

### 체중 (`cogs/weight.py`)
- `WeightInputModal`: 체중 입력 Modal (먹구름봇 메인 버튼에서 호출)
- 목표 달성 알림은 체중관리봇에서 담당하지만, 현재 `cogs.weight`는 먹구름봇에서도 로드함 (v3.2 현재)

---

## 4. 영구 버튼 등록 (`bot.py on_ready`)

```python
bot.add_view(MainView())    # 메인 버튼 (custom_id 기반 영구 복원)
bot.add_view(StartView())   # 시작하기 버튼
```

---

## 5. 중요 제약

| 제약 | 이유 |
|------|------|
| hp/hunger/mood 수치 절대 노출 금지 | UX 원칙 — 내부 로직용 |
| 날씨는 별도 알림 없음 | 기상 시간에 날씨봇이 이미지 교체로만 전달 |
| 칼로리/영양소는 Ephemeral로만 확인 | 하루정리 버튼 클릭 시만 노출 |
| 이미지 파일명 소문자 | `eat.png` O, `Eat.PNG` X |
