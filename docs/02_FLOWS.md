# 기능 흐름 (Flows)

## 메인 Embed UI

```
[다마고치 이미지 — 파일 첨부로 크게 표시]
──────────────────────────────────────
[Embed] {tamagotchi_name}의 하루 · "GPT 대사"

Row 0: [ 🍽️ 식사 입력 ] [ 📊 오늘 요약 ] [ 📅 오늘 일정 ]
Row 1: [ ⚙️ 설정 변경 ] [ ⏰ 시간 설정 ] [ ⚖️ 체중 기록 ]
```

> 이미지는 `file=img_file`로 첨부 전송되어 embed 위에 크게 표시됨.  
> embed 내부에는 `set_thumbnail()` 미사용.

### 버튼 동작

| 버튼 | 동작 | 출력 |
|------|------|------|
| 🍽️ 식사 입력 | MealInputModal 팝업 | 텍스트 자연어 입력 → GPT 분석 → DB 저장 → Embed 갱신 |
| 📊 오늘 요약 | Ephemeral | 총칼로리/탄단지/끼니별 내역/GPT 코멘트 |
| 📅 오늘 일정 | Ephemeral | 목표칼로리/체중현황(ML)/식사알림시간/날씨/GPT 코멘트 |
| ⚙️ 설정 변경 | SettingsModal | 이름/도시/목표체중 변경 |
| ⏰ 시간 설정 | TimeStep1View | Select Menu 2단계 → 기상/식사 알림 시간 변경 |
| ⚖️ 체중 기록 | WeightInputModal | 체중 입력 → DB 저장 → 목표 달성 판정 → Embed 갱신 |

---

## 온보딩 흐름

```
[🐣 다마고치 시작하기] 클릭
  → OnboardingModal (4개 필드)
    fields: tamagotchi_name, city, weight_info(현재/목표),
            body_info(성별/나이/키)
    ※ 시간 설정은 완료 후 별도 단계로 분리
  → GPT-4o: daily_cal_target 계산 (Mifflin-St Jeor)
  → DB users + tamagotchi 저장 (hp=100, hunger=100, mood=100)
    ※ 시간 기본값: wake=07:00 / 아침=08:00 / 점심=12:00 / 저녁=18:00
  → #다마고치 채널에 유저 전용 쓰레드 생성
  → 쓰레드에 메인 Embed 전송 + embed_message_id 저장
  → APScheduler에 날씨 Job 자동 등록 (07:00 기본값)
  → Ephemeral: "✅ 설정 완료! 이제 시간을 설정해줘 ⏰"
  → Ephemeral: TimeStep1View (시간 설정 1단계 Select Menu)

기존 유저가 버튼 클릭 시:
  → Ephemeral: "이미 등록되어 있어! 쓰레드 확인해봐 😊"
```

---

## 식사 입력 흐름

### 텍스트 입력 (🍽️ 식사 입력 버튼)
```
MealInputModal → 자유 텍스트 입력
  → GPT parse_meal_input(): days_ago, meal_type, food_name 추출
    - "어제 저녁에 치킨 먹었어" → days_ago=1, meal_type=저녁, food_name=치킨
    - 소급 입력 지원 (1~2일 전)
  → GPT analyze_meal_text(): 칼로리 + 영양소 분석
  → ML 칼로리 보정 (get_corrected_calories)
  → DB meals 저장
  → hunger/mood/hp 수치 갱신 (오늘 입력 시만)
  → Ephemeral: 분석 결과 표시
  → Embed: eating.png로 교체 → 3분 후 자동 복구
```

### 사진 입력 (쓰레드에 이미지 첨부)
```
on_message 이벤트로 사진 감지 (본인 전용 쓰레드에서만)
  → "📸 음식 사진이에요? [✅ 분석하기] [❌ 아니야]" 버튼 전송
  → [✅ 분석하기] 클릭
    → GPT-4o Vision API 호출 (image_url)
    → 분석 결과 Embed + [✅ 기록하기] [❌ 취소]
  → [✅ 기록하기] 클릭
    → ML 칼로리 보정
    → DB meals 저장 (input_method='photo')
    → hunger/mood/hp 수치 갱신
    → Embed 갱신
```

### 오후 10시 칼로리 자동 판정 (SchedulerCog)
```
매일 22:00 자동 실행
  → 전체 유저 순회
  → 식사 기록 없으면: 알림 메시지만 전송
  → 식사 기록 있으면:
    if total_cal > daily_cal_target       → overfed 판정
    if total_cal < daily_cal_target × 0.67 → underfed 판정
    → _send_daily_analysis() → 하루 결산 Embed 전송
    → Embed 이미지 갱신 (overfed/underfed/정상)
```

---

## 날씨 흐름

```
APScheduler → 유저별 wake_time 도달
  → 기상청 초단기실황 API (도시명 → nx,ny 격자좌표 자동 변환)
  → 에어코리아 API (PM10, PM2.5)
  → DB weather_log 저장
  → GPT: 날씨 기반 대사 생성 (수치 직접 언급 금지)
  → 쓰레드에 날씨 Embed 전송 (미세먼지 등급 포함)
  → create_or_update_embed() → 날씨 기반 이미지로 교체
  ※ 별도 알림 메시지 없음. 이미지 교체로만 날씨 전달.
```

---

## 식사 알림 흐름

```
[식사시간 -30분] → _meal_reminder()
  → 쓰레드 알림: "{tamagotchi_name}이(가) 슬슬 배가 고파지고 있어!"

[식사시간 정각] → _meal_upset() (미입력 시)
  → GPT 대사 생성 (배고파서 말해줘)
  → create_or_update_embed() → upset.png 교체

[식사시간 +1시간] → _meal_late() (미입력 시)
  → GPT 대사 생성 (1시간 넘게 못 먹어서 슬퍼)
  → 쓰레드에 대사 메시지 전송

[밥 주기 입력 감지]
  → eat.png 3분 표시 → 자동 복구
  ※ 패널티 없음. upset 상태에서도 밥 주면 즉시 정상 복구.

[매 시간 정각] → _hourly_hunger_decay()
  → 전체 유저 hunger -5 (최소 0)
  → hunger < 40 이 되면 자연스럽게 upset.png 트리거

[Job 등록 시점]
  → 봇 시작 (on_ready): register_all_users() — 전체 유저 일괄 등록
  → 온보딩 완료: register_meal_jobs(user_id) — 기본 시간 기준 등록
  → 시간 설정 저장: register_meal_jobs(user_id) — 새 시간으로 재등록
```

---

## 시간 설정 흐름

```
[⏰ 시간 설정] 클릭 (메인 Embed) 또는 온보딩 완료 후 자동 유도
  → TimeStep1View (Ephemeral)
    🌅 기상 시간 — 시(0~23) / 분(00~50, 10분 단위)
    🍳 아침 알림 — 시(0~23) / 분(00~50, 10분 단위)
    [다음 →] 버튼 클릭
  → TimeStep2View (같은 메시지 edit)
    🌞 점심 알림 — 시(0~23) / 분(00~50, 10분 단위)
    🌙 저녁 알림 — 시(0~23) / 분(00~50, 10분 단위)
    [✅ 저장] 버튼 클릭
      → DB update_user(wake_time, breakfast_time, lunch_time, dinner_time)
      → WeatherCog 스케줄러 재등록 (새 wake_time 적용)
      → Ephemeral: "⏰ 시간 설정 완료!" (설정값 요약)
```

---

## 설정 변경 흐름

```
[⚙️ 설정 변경] 클릭
  → SettingsModal (현재 값이 미리 채워짐)
    fields: 다마고치 이름, 거주 도시, 목표 체중
    ※ 시간 설정은 [⏰ 시간 설정] 버튼에서 별도 진행
  → 변경 감지 후:
    - 이름 변경 → DB + 쓰레드 이름 변경
    - 도시 변경 → DB 업데이트
    - 목표 체중 변경 → DB + GPT 권장 칼로리 재계산
```

---

## 체중 기록 흐름

```
[⚖️ 체중 기록] 클릭
  → WeightInputModal → 체중 입력 (kg)
  → DB weight_log 저장
  → 목표 체중 달성 여부 판정
  → 체중 변화 + 달성률 바 + GPT 대사 → Ephemeral Embed
  → 목표 달성 시: Embed 이미지 cheer.png로 교체
```
