# 먹구름봇 — 주요 흐름 상세

---

## 1. 온보딩 흐름

```
관리자: /start
  → OnboardingCog.start_cmd()
  → 채널에 시작 Embed + StartView 전송 (고정)

유저: "🥚 시작하기" 클릭
  → StartView.start_button()
  → 이미 등록 + 쓰레드 존재? → "이미 등록됨" 안내
  → 미등록 또는 쓰레드 없음? → OnboardingModal 열기

유저: 모달 제출 (이름/도시/체중/신체정보)
  → OnboardingModal.on_submit()
  → 1. 체중 파싱: "76/70" → init_weight=76, goal_weight=70
  → 2. 신체정보 파싱: "남/25/175" → gender, age, height
  → 3. calculate_daily_calories() → GPT로 권장 칼로리 계산
  → 4. create_user() + create_tamagotchi()
  → 5. 전용 쓰레드 5개 생성 + DB 저장
       thread_id, mail_thread_id, meal_thread_id, weather_thread_id, weight_thread_id
  → 6. WeatherCog.register_user_job(wake_time) — 날씨 스케줄러 등록
  → 7. SchedulerCog.register_meal_jobs(user_id) — 식사 알림 등록
  → 8. 메인 Embed 생성 (create_or_update_embed)
  → 9. TimeStep1View 팝업 (기상/식사 시간 설정)
```

---

## 2. 식사 입력 흐름 (텍스트)

```
유저: "🍽️ 식사 입력" 클릭 (MainView)
  → meal_button()
  → send_message(MealInputSelectView, ephemeral=True)

유저: "📝 텍스트로 입력" 클릭
  → MealInputSelectView.text_btn()
  → send_modal(MealInputModal)  ← utils/embed.py에 정의

유저: 모달 제출 ("어제 저녁에 치킨 먹었어")
  → MealInputModal.on_submit()
  → 1. parse_meal_input() → {days_ago:1, meal_type:"저녁", food_name:"치킨"}
  → 2. search_food_nutrition("치킨") → 식약처 DB 조회
         없으면 analyze_meal_text() fallback
  → 3. get_corrected_calories() — ML 보정
  → 4. generate_comment("치킨 먹었어, 반응해줘!")
  → 5. create_meal(..., recorded_date=target_date)
  → 6. 오늘 식사 아닌 경우(is_past=True): tamagotchi 수치 변경 없음
     오늘 식사: hunger/mood/hp 갱신
  → 7. Ephemeral 결과 전송 (칼로리/영양소/총 칼로리)
  → 8. 오늘 식사 → create_or_update_embed(just_ate=True)
     → 3분 후 자동으로 normal 상태 Embed 복원 (asyncio.sleep(180))
  → 9. 소급 입력 + 아침/점심/저녁 모두 완료 → _send_daily_analysis()
```

---

## 3. 식사 입력 흐름 (사진)

```
유저: "📸 사진으로 입력" 클릭
  → MealInputSelectView.photo_btn()
  → set_meal_waiting(user_id, seconds=60) — DB에 만료 시각 저장
  → meal_thread_id 있으면: "🍽️ {meal_thread.mention} 에 올려줘 (60초)"
  → 없으면: "지금 이 채팅에 올려줘 (60초)"

[식사봇 on_message 처리]
  → is_meal_waiting(user_id) → True
  → clear_meal_waiting(user_id)
  → GPT-4o Vision 분석 → Embed 전송 (식사봇 담당)
```

---

## 4. 하루 정리 흐름

```
유저: "📋 하루 정리" 클릭 (MainView)
  → daily_button()
  → defer(ephemeral=True)
  → 1. get_today_meals(), get_today_calories()
  → 2. get_weight_history(limit=7) — 체중 기반 목표 칼로리 동적 조율
       최근 체중 ↑ → target_cal * 0.95
       최근 체중 ↓ → target_cal * 1.05 (목표까지 2kg 이상 남았을 때만)
  → 3. get_latest_weather() — 날씨 정보
  → 4. analyze_eating_patterns() — 식사 패턴 컨텍스트
  → 5. generate_comment(통합 컨텍스트)
  → Embed 구성:
       - 칼로리 현황 (바 그래프)
       - 탄단지 비율
       - 끼니별 내역
       - 체중 현황 + 프로그레스 바
       - 날씨 정보
       - 식사 알림 시간
       - 타마고치 한마디
  → followup.send(embed, ephemeral=True)
```

---

## 5. 설정 흐름

```
유저: "⚙️ 설정" 클릭 (MainView)
  → SettingsSubView 팝업 (ephemeral)
  → 항목 선택: 도시 변경 / 체중 목표 변경 / 이메일 설정

[도시 변경]
  → CityChangeModal → update_user(city=...)

[체중 목표 변경]
  → GoalWeightModal → update_user(goal_weight=..., daily_cal_target=...)

[이메일 설정]
  → EmailSubView → "이메일 설정" / "발신자 관리" 선택
  → EmailSetupModal (utils/email_ui.py 공유 Modal)
```

---

## 6. 시간 설정 흐름 (온보딩 후 또는 설정에서)

```
TimeStep1View (기상 시간)
  → 선택: 05:00 ~ 10:00
  → update_user(wake_time=...)
  → WeatherCog.register_user_job(wake_time)
  → TimeStep2View 팝업

TimeStep2View (아침 알림)
  → 선택 또는 "건너뛰기"

TimeStep3View (점심 알림)
  → ...

TimeStep4View (저녁 알림)
  → update_user(breakfast_time, lunch_time, dinner_time)
  → SchedulerCog.register_meal_jobs(user_id)  ← 식사 알림 재등록
```

---

## 7. 오후 10시 자동 칼로리 판정

```
매일 22:00 (_nightly_analysis)
  ├── 식사 없음: "오늘 식사 기록이 없어!" + 스트릭 초기화
  └── 식사 있음:
        _send_daily_analysis()
          → 과식/소식/정상 판정
          → 일일 결산 Embed
        streak + 1 → update_streak()
        check_new_badges() → 새 배지 있으면:
          add_badges()
          배지 Embed 전송
          create_or_update_embed(goal_achieved=True)  ← cheer.png
```
