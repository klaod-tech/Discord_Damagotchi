# 기능 흐름 (Flows)

> last_updated: 2026-04-13 | 현재 버전: v3.2
>
> 각 흐름 앞의 **[봇이름]** 태그는 해당 흐름을 실제 처리하는 봇 프로세스를 나타냄.

---

## 메인봇 UX — 자연어 대화 방식 (v4.0 목표)

> **버튼 Embed 방식 폐기 예정** — 유저 전용 채널에서 자연어로 소통하는 오케스트레이터 방식으로 전환.

```
유저 전용 채널 (#{이름}-채팅창)
┌─────────────────────────────────────────────┐
│ [📌 고정] 캐릭터 상태 Embed                   │
│   {tamagotchi_name}의 하루 · "GPT 대사"        │
│   [다마고치 이미지]                             │
├─────────────────────────────────────────────┤
│ 유저: "나 오늘 점심에 비빔밥 먹었어"              │
│ 봇:  칼로리 분석 결과 Embed (직접 응답)           │
├─────────────────────────────────────────────┤
│ 유저: (사진 첨부)                              │
│ 봇:  "음식 사진이에요? [✅ 분석] [❌ 아니야]"     │
└─────────────────────────────────────────────┘

유저: "나 오늘 점심에 비빔밥 먹었어"
  → 먹구름봇 on_message 감지
  → GPT/ML 의도 분류 → task_queue INSERT
  → 식사봇 poll → 처리 → personal_channel에 직접 응답

유저: "내일 오후 3시 병원 예약 있어"
  → 먹구름봇 on_message 감지
  → GPT/ML 의도 분류 → task_queue INSERT
  → 일정봇 poll → 처리 → personal_channel에 직접 응답
  → APScheduler: 지정 시간에 info_thread에 알림 전송
```

> **핵심 설계**: 서브봇은 `personal_channel_id`로 직접 응답. 메인봇으로 반환하지 않음.  
> 쓰레드는 **Push 알림 전용** (날씨/일정 → `info_thread_id`, 메일 → `mail_thread_id`).

### 자연어 트리거 목록

| 발화 예시 | 감지 의도 | 처리 봇 | 서브봇 응답 위치 |
|-----------|-----------|---------|-----------|
| "점심에 비빔밥 먹었어" | meal | 식사봇 | 유저 전용 채널 (직접 응답) |
| 사진 직접 업로드 | meal_photo | 식사봇 | 유저 전용 채널 (직접 응답) |
| "몸무게 기록할게, 68kg" | weight | 체중관리봇 | 유저 전용 채널 (직접 응답) |
| "오늘 하루 어떻게 지냈는지 적고 싶어" | diary | 일기봇 | 유저 전용 채널 (직접 응답) |
| "다음 주 월요일 팀 미팅 있어" | schedule | 일정봇 | 유저 전용 채널 (직접 응답) + 알림 쓰레드 |

### 슬래시 커맨드 (기능 접근 경로)

| 커맨드 | 동작 |
|--------|------|
| `/설정` | SettingsSubView: 내정보/위치/시간/이메일 |
| `/하루정리` | Ephemeral: 오늘 칼로리·영양소·끼니·체중·날씨 |
| `/음식추천` | n8n 웹훅 → 주변 음식 추천 (Ephemeral) |

---

## 메인 Embed UI (v3.2 현재 — 버튼 5개 방식)

> **이 방식은 v4.0 전환 전까지 유지.** 전환 후 캐릭터 상태 Embed만 고정 메시지로 남기고 버튼 제거.

```
[다마고치 이미지 — 파일 첨부로 크게 표시]
──────────────────────────────────────
[Embed] {tamagotchi_name}의 하루 · "GPT 대사"

Row 0: [ 🍽️ 식사 입력 ] [ 📋 하루 정리 ] [ 🍜 뭐 먹고 싶어? ]
Row 1: [ ⚙️ 설정 ]      [ ⚖️ 체중 기록 ]
```

| 버튼 | 처리 봇 | 동작 | 출력 위치 |
|------|---------|------|-----------|
| 🍽️ 식사 입력 | 먹구름봇 (텍스트) / 식사봇 (사진) | 텍스트 → MealInputModal / 사진 → DB 대기 상태 | 메인 쓰레드 |
| 📋 하루 정리 | 먹구름봇 | Ephemeral: 칼로리·탄단지·끼니·체중·날씨 | Ephemeral |
| 🍜 뭐 먹고 싶어? | 먹구름봇 | n8n 웹훅 (연동 예정) | Ephemeral |
| ⚙️ 설정 | 먹구름봇 | SettingsSubView | Ephemeral |
| ⚖️ 체중 기록 | 먹구름봇* | WeightInputModal → DB 저장 | Ephemeral + 체중 쓰레드 |

---

## 온보딩 흐름 — [먹구름봇]

### v4.0 목표 (유저별 전용 채널 방식)

```
#먹구름-시작 채널의 [🐣 다마고치 시작하기] 클릭
  → OnboardingModal (5개 필드)
      - tamagotchi_name: 캐릭터 이름
      - city: 거주 도시 (날씨 API용, 시 단위)
      - address: 동네 주소 (음식 추천용, 구/동 단위, 예: "마포구 합정동")
      - weight_info: "현재체중/목표체중" 형식
      - body_info: "성별/나이/키" 형식 (칼로리 계산용)
    ※ 시간 설정은 완료 후 별도 단계로 분리

  → GPT-4o: Mifflin-St Jeor 공식으로 daily_cal_target 계산
  → DB users + tamagotchi 저장 (hp=100, hunger=100, mood=100)
      기본값: wake=07:00 / 아침=08:00 / 점심=12:00 / 저녁=18:00

  → "먹구름" 카테고리에 유저 전용 채널 생성:
      #{이름}-채팅창  → personal_channel_id 저장
      ※ 권한 설정: 해당 유저만 읽기/쓰기 가능

  → 전용 채널 안에 쓰레드 생성 (총 2개 — Push 알림 전용):
      1. 🔔 {이름}의 알림      → info_thread_id  (날씨 매일 기상 + 일정 D-day)
      2. 📧 {이름}의 메일함    → mail_thread_id  (메일봇 전용)

  → 전용 채널에 캐릭터 Embed 고정 (pin) + embed_message_id 저장
  → SchedulerCog.register_meal_jobs(user_id) 호출
  → WeatherCog: info_thread_id 기준 wake_time Job 등록
  → Ephemeral: "✅ 설정 완료! 이제 #{이름}-채팅창 에서 대화해줘 ⏰"
  → Ephemeral: TimeStep1View (시간 설정 1단계)

기존 유저가 버튼 클릭 시:
  → Ephemeral: "이미 등록되어 있어! #{이름}-채팅창 채널을 확인해봐 😊"
```

### v3.2 현재 (쓰레드 방식 — 기존 유저 호환)

```
[🐣 다마고치 시작하기] 클릭
  → OnboardingModal (4개 필드: 이름/도시/체중/신체정보)
  → GPT-4o: 칼로리 계산
  → DB users + tamagotchi 저장
  → #다마고치 채널에 유저 전용 쓰레드 5개 생성:
      1. {이름}의 구름      → thread_id (메인, fallback 기준)
      2. {이름}의 식사 기록 → meal_thread_id
      3. {이름}의 날씨      → weather_thread_id
      4. {이름}의 체중관리  → weight_thread_id
      5. {이름}의 메일함    → mail_thread_id
  → 메인 쓰레드에 캐릭터 Embed 전송 + embed_message_id 저장
  → 시간 설정 팝업
```

---

## 식사 입력 흐름

### 텍스트 입력 — [먹구름봇]

```
[🍽️ 식사 입력] → [📝 텍스트로 입력] 클릭
  → MealInputModal 팝업
    → GPT parse_meal_input():
        "어제 저녁에 치킨 먹었어" → days_ago=1, meal_type=저녁, food_name=치킨
        소급 입력 지원 (1~2일 전)
    → 식약처 API (1순위) → GPT fallback (2순위)로 칼로리/영양소 분석
    → ML 칼로리 보정 (get_corrected_calories)
    → 칼로리 = 0이면 저장 차단 (오류 안내 반환)
    → DB meals 저장 (input_method='text')
    → hunger / mood / hp 수치 갱신
    → 메인 쓰레드 Embed: eat.png → 3분 후 자동 복구
    → Ephemeral: 분석 결과 표시
```

### 사진 입력 — 유저 전용 채널 직접 업로드 — [식사봇]

> v4.0부터 식사 사진은 유저 전용 채널(`personal_channel_id`)에 직접 업로드.  
> 별도 식사 쓰레드 없음. 대기 상태(`meal_waiting`) 기반 버튼 흐름 폐기.

```
[식사봇] personal_channel_id에 이미지 첨부 감지
  → on_message: 이미지 있는 메시지 + personal_channel_id 채널인지 확인
  → "📸 음식 사진이에요? [✅ 분석하기] [❌ 아니야]"
  → [✅ 분석하기]: GPT-4o Vision API 호출
  → 분석 결과 Embed + [✅ 기록하기] [❌ 취소]

[✅ 기록하기] 클릭
  → ML 칼로리 보정
  → 칼로리 = 0이면 저장 차단
  → DB meals 저장 (input_method='photo')
  → hunger / mood / hp 수치 갱신
  → personal_channel_id 채널 캐릭터 Embed 갱신
```

> **v3.2 하위 호환**: `meal_waiting` 패턴 + `meal_thread_id` fallback은 기존 유저용으로 유지.

---

## 날씨 흐름 — [날씨봇]

> **Push 전용 흐름**: 날씨봇은 유저가 요청하지 않아도 자동 전송. 응답 위치 = `info_thread_id`.

```
[날씨봇] APScheduler → 유저별 wake_time 도달
  → 기상청 초단기실황 API (도시명 → nx,ny 격자좌표 자동 변환, 50개+ 도시 지원)
  → 에어코리아 API (PM10, PM2.5)
  → 이미지 선택 (우선순위):
      PM10>80 or PM2.5>35 → wear_mask.png
      강수 = 비            → rainy.png
      강수 = 눈            → snow.png
      기온 ≥ 26°C          → hot.png
      기온 ≤ 5°C           → warm.png
      하늘 흐림             → tired.png
      하늘 구름많음         → smile.png
      맑음                  → normal.png
  → DB weather_log 저장
  → info_thread_id or thread_id 쓰레드에 날씨 Embed 전송  ← Push 알림 전용 쓰레드
      ※ 수치(기온·PM 수치) 미표시, 캐릭터 이미지+자연어 문장으로만 전달
  → personal_channel_id 채널 캐릭터 Embed: 날씨 기반 이미지로 교체

새 유저 스케줄 등록:
  → 날씨봇 on_ready: 전체 유저 wake_time 기준 Job 일괄 등록
  → 1시간 주기: DB 전체 유저 재점검 → 누락된 Job 자동 등록
```

---

## 이메일 모니터링 흐름 — [메일봇]

```
[메일봇] APScheduler 1분 간격 → _poll_all_users()
  → get_email_users(): naver_email/naver_app_pw 설정 유저 전체 조회
  → 유저별 _poll_user() 실행

_poll_user(user):
  → fetch_new_emails() [IMAP executor 오프로드]
      imap.naver.com:993 / INBOX
      email_last_uid 이후 메일만 조회

  스팸 필터 3단계:
    1단계: INBOX만 조회 (스팸함 제외)
    2단계: 제목 키워드 필터
           ([광고][AD][홍보][이벤트][공지] 수신거부 Unsubscribe 등)
    3단계: email_senders 화이트리스트 (미등록 발신자 무시)

  → 본문 길이 판단:
      ≤200자 → 원문 그대로 Embed
      >200자  → GPT 요약 후 Embed
  → email_log 저장
  → update_email_last_uid() → 중복 처리 방지
  → mail_thread_id or thread_id 쓰레드에 Embed 전송:  ← Push 전용 쓰레드
      📬 새 메일이 도착했어요!
      ✉️ 발신자: {별명} <{email}>
      📅 발송 일시: YYYY-MM-DD HH:MM (KST)
      📝 내용: {원문 or GPT 요약}
```

### 이메일 슬래시 커맨드 — [메일봇]

| 커맨드 | 동작 |
|--------|------|
| `/이메일설정` | EmailSetupModal → 네이버 아이디 + 앱 비밀번호 저장 |
| `/발신자추가` | SenderAddModal → 이메일 + 별명 등록 |
| `/발신자목록` | 등록된 발신자 목록 Ephemeral 표시 |
| `/발신자삭제` | Select 드롭다운 → 선택 즉시 삭제 |

---

## 체중 기록 흐름 — [먹구름봇*]

> *현재 cogs.weight가 bot.py에 임시 로드됨. bot_weight.py 분리 후 [체중관리봇]으로 이전.

```
[⚖️ 체중 기록] 클릭
  → WeightInputModal → 체중 입력 (kg)
  → DB weight_log 저장
  → 목표 체중 달성 여부 판정:
      달성: cheer.png, 달성률 100%, 축하 GPT 대사
      미달: 달성률 바 (░░░░░░░░░) + 현재 gap 표시
  → Ephemeral: 체중 변화 + 달성률 + GPT 대사 Embed
  → (분리 후) personal_channel_id에 직접 응답 (체중은 push가 아닌 유저 요청 응답이므로 채널)
```

---

## 스케줄러 흐름 — [먹구름봇]

```
[매일 22:00] _nightly_analysis()
  → 전체 유저 순회 (메인 thread_id 쓰레드 대상)
  → 식사 기록 없으면:
      "밥은 먹었어?" 메시지 전송
      streak = 0 초기화 (≥3이었다면 아쉬운 메시지 추가)
  → 식사 기록 있으면:
      total_cal 판정:
        > daily_cal_target        → overfed
        < daily_cal_target × 0.67 → underfed
        그 외                     → 정상
      _send_daily_analysis() → 하루 결산 Embed 전송
      Embed 이미지 갱신
      streak +1, max_streak 갱신
      check_new_badges() → 신규 배지 확인
      배지 있으면: 골드 Embed (🏅) + cheer.png Embed 갱신

[매 시간 정각] _hourly_hunger_decay()
  → 전체 유저 hunger -5 (최소 0)

[식사 알림 — 유저별 3단계 Job]
  식사시간 -30분 → _meal_reminder()
    → 메인 쓰레드: "{이름}이(가) 슬슬 배가 고파지고 있어!"
    ※ TODO: meal_thread_id or thread_id 로 변경 예정
  식사시간 정각  → _meal_upset() (미입력 시)
    → GPT 대사 (배고파서) + upset.png Embed 갱신
  식사시간 +1시간 → _meal_late() (미입력 시)
    → GPT 대사 (1시간 넘게 못 먹어서 슬퍼) 메시지 전송

  [Job 등록 시점]
    봇 시작 on_ready → register_all_users() (전체 일괄)
    온보딩 완료      → register_meal_jobs(user_id)
    시간 설정 저장   → register_meal_jobs(user_id) (재등록)

[매주 일요일 03:00] _weekly_ml_retrain()
  → retrain_all_users() — 전체 유저 칼로리 보정 모델 재학습
  ※ TODO: bot_meal.py로 이전 예정 (식사 ML이므로)

[매주 일요일 08:00] _weekly_report()
  → 전체 유저 메인 쓰레드에 주간 Embed 전송:
      🔥 칼로리 평균 / 목표 달성일 / 기록일
      🍽️ 끼니 커버리지 (아침·점심·저녁 × 7일)
      🏆 이번 주 최다 음식
      ⚖️ 체중 변화 (weight_log 7일 비교)
      🔥 연속 기록 스트릭
      🏅 보유 배지
      🐣 GPT 주간 응원 코멘트
  ※ 체중 섹션은 bot_weight.py 분리 후 체중관리봇 스케줄러로 이전 예정
```

---

## 시간 설정 흐름 — [먹구름봇]

```
[⚙️ 설정] → [⏰ 시간 설정] 또는 온보딩 완료 후 자동 유도
  → TimeStep1View (Ephemeral)
      🌅 기상 시간  시(0~23) / 분(00~50, 10분 단위)
      🍳 아침 알림  시(0~23) / 분(00~50, 10분 단위)
      [다음 →]
  → TimeStep2View (메시지 edit)
      🌞 점심 알림  시(0~23) / 분(00~50, 10분 단위)
      🌙 저녁 알림  시(0~23) / 분(00~50, 10분 단위)
      [✅ 저장]
        → DB update_user(wake_time, breakfast_time, lunch_time, dinner_time)
        → WeatherCog 스케줄러 재등록 (새 wake_time)
        → SchedulerCog.register_meal_jobs(user_id) 재등록
        → Ephemeral: "⏰ 시간 설정 완료!" (설정값 요약)
```

---

## 설정 변경 흐름 — [먹구름봇]

```
[⚙️ 설정] 클릭
  → SettingsSubView (Ephemeral)
      Row 0: [👤 내 정보] [📍 위치 설정] [⏰ 시간 설정]
      Row 1: [📧 이메일 설정]

  [👤 내 정보] → InfoModal (캐릭터 이름, 목표체중)
    → 이름 변경: DB 업데이트 + 쓰레드 이름 변경
    → 목표체중 변경: DB 업데이트 + GPT 칼로리 재계산

  [📍 위치 설정] → CityModal (거주 도시)
    → DB 업데이트 → 날씨 API 즉시 반영

  [⏰ 시간 설정] → TimeStep1View (위 시간 설정 흐름과 동일)

  [📧 이메일 설정] → EmailSubView (Ephemeral)
      Row 0: [📬 발신자 추가] [📋 발신자 목록] [🗑️ 발신자 삭제]
      Row 1: [✏️ 이메일 수정]
    → 각 버튼은 utils/email_ui.py의 공통 Modal 사용
    → [✏️ 이메일 수정]: EmailSetupModal
        mail_thread_id 없으면 메일 스레드 자동 생성
```

---

## 미구현 흐름 (구상 단계)

### 일기봇 흐름 (v3.4 — UX 구상 단계)

```
[예상 흐름]
자연어: "오늘 하루 적고 싶어" → 먹구름봇 감지 → 일기봇 트리거
  또는 /일기작성 슬래시 커맨드
  → DiaryInputModal (500자 자유 작성)
  → GPT 감정 분석: 긍정/부정/중립 + 감정 키워드
  → DB diary_log 저장
  → diary_thread_id 쓰레드에 감정 Embed 전송
매주 일요일 09:00 → 주간 감정 리포트 자동 전송
```

### 일정봇 흐름 (v3.5 — UX 구상 단계)

```
[예상 흐름]
자연어: "다음 주 월요일 병원 예약 있어" → 먹구름봇 감지 → 일정봇 트리거
  또는 /일정등록 슬래시 커맨드
  → ScheduleInputModal (제목, 날짜, 시간, 반복)
  → DB schedules 저장
  → APScheduler DateTrigger → 지정 시간 알림
  → schedule_thread_id 쓰레드에 알림 Embed 전송
매일 08:00 → 오늘 일정 브리핑 자동 전송
```

### 오케스트레이터 자연어 라우팅 (v4.0 예정)

```
유저 전용 채널에서 자유롭게 채팅
  → 먹구름봇 on_message 감지
  → [1단계] GPT 의도 분류 (meal/diary/schedule/weight/none)
    → task_queue 테이블 삽입 (bot_target, user_id, payload)
    → intent_log 저장 (학습 데이터 축적)
  → 각 전문봇 30초 폴링 → 태스크 처리 → 전용 쓰레드에 결과 전송

  → [2단계, v4.0 이후] ML 의도 분류기 (50건+ 누적 시)
    TF-IDF + LogisticRegression으로 GPT 의도 분류 대체
    GPT는 엔티티 추출만 담당 (비용 절감 + 개인화)

예: "오늘 점심에 비빔밥이랑 콜라 먹었어"
  → 식사봇 트리거 (비빔밥, 콜라 각각 분석)
예: "다음 주에 제주도 여행 가"
  → 일정봇 트리거 + 날씨봇 트리거 (제주도 날씨 미리 조회)
```
