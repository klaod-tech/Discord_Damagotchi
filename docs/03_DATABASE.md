# DB 스키마 — Supabase (PostgreSQL)

> last_updated: 2026-05-04 | 브랜치: feat/web-migration  
> **연결 방식**: Supabase JS Client (`@supabase/supabase-js`)  
> **인증**: Supabase Auth (이메일 로그인, RLS로 유저별 격리)

---

## 테이블 목록

| 테이블 | 소유 | 설명 |
|--------|------|------|
| `users` | React 온보딩 | 유저 프로필, 설정, 이메일 정보 |
| `tamagotchi` | React | 캐릭터 상태 (hp/hunger/mood) |
| `meal_log` | n8n MealBOT | 식사 기록 |
| `diary` | n8n DiaryBOT | 일기 + 요약 |
| `schedule` | n8n ScheduleBOT | 일정 |
| `weight_log` | n8n WeightManageBOT | 체중 기록 + BMI |
| `weather_log` | n8n WeatherBOT | 날씨 기록 |
| `email_log` | n8n EmailBOT | 이메일 수신 기록 |
| `food_feedback` | n8n FoodRecommend | 음식 추천 피드백 |
| `chat_logs` | (예정) | 대화 기록 |

---

## users

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `user_id` | TEXT PK | Supabase Auth UID |
| `tamagotchi_name` | TEXT | 캐릭터 이름 |
| `city` | TEXT | 도시 (날씨 API용) |
| `village` | TEXT | 동 단위 주소 (음식 추천용) |
| `gender` | TEXT | 성별 |
| `age` | INTEGER | 나이 |
| `height` | REAL | 키 (cm) |
| `init_weight` | REAL | 초기 체중 |
| `goal_weight` | REAL | 목표 체중 |
| `daily_cal_target` | INTEGER | 일일 칼로리 목표 |
| `wake_time` | TEXT | 기상 시간 (HH:MM) |
| `breakfast_time` | TEXT | 아침 식사 시간 |
| `lunch_time` | TEXT | 점심 식사 시간 |
| `dinner_time` | TEXT | 저녁 식사 시간 |
| `snack_time` | TEXT | 간식 시간 |
| `allergies` | ARRAY | 알레르기 목록 |
| `food_preferences` | ARRAY | 음식 선호도 |
| `email_provider` | TEXT | 이메일 제공자 (네이버/구글/다음) |
| `email_address` | TEXT | 이메일 주소 |
| `email_app_pw` | TEXT | 앱 비밀번호 |
| `email_last_uid` | TEXT | 마지막 수신 이메일 UID |
| `created_at` | TIMESTAMP | 가입일 |
| `updated_at` | TIMESTAMP | 마지막 수정일 |

---

## tamagotchi

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `user_id` | TEXT PK | Supabase Auth UID |
| `hp` | INTEGER | 체력 (0~100, 직접 노출 금지) |
| `hunger` | INTEGER | 배고픔 (0~100, 직접 노출 금지) |
| `mood` | INTEGER | 기분 (0~100, 직접 노출 금지) |
| `current_image` | TEXT | 현재 이미지 파일명 |
| `last_fed_at` | TIMESTAMP | 마지막 식사 시각 |
| `updated_at` | TIMESTAMP | 마지막 업데이트 |

> **핵심 원칙**: hp/hunger/mood 수치는 절대 유저에게 직접 노출 금지. 이미지+대사로만 간접 표현.

---

## meal_log

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID PK | |
| `user_id` | TEXT | Supabase Auth UID |
| `date` | DATE | 식사 날짜 |
| `meal_type` | TEXT | breakfast/lunch/dinner/snack |
| `food_name` | TEXT | 음식 이름 |
| `calories` | INTEGER | 칼로리 |
| `created_at` | TIMESTAMP | |

---

## diary

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID PK | |
| `user_id` | TEXT | |
| `date` | DATE | 일기 날짜 |
| `content` | TEXT | 일기 내용 |
| `summary` | TEXT | GPT 요약/핵심 키워드 |
| `created_at` | TIMESTAMP | |

---

## schedule

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID PK | |
| `user_id` | TEXT | |
| `title` | TEXT | 일정 제목 |
| `description` | TEXT | 상세 내용 |
| `location` | TEXT | 장소 |
| `date` | DATE | 날짜 |
| `time` | TEXT | 시간 (HH:MM) |
| `is_done` | BOOLEAN | 완료 여부 |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

---

## weight_log

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `user_id` | TEXT | |
| `date` | DATE | 기록 날짜 |
| `weight` | REAL | 체중 (kg) |
| `bmi` | REAL | BMI |
| `note` | TEXT | 메모 |
| `created_at` | TIMESTAMP | |

---

## weather_log

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID PK | |
| `user_id` | TEXT | |
| `date` | DATE | 날짜 |
| `city` | TEXT | 도시 |
| `temperature` | REAL | 기온 |
| `condition` | TEXT | 맑음/흐림/비/눈 |
| `humidity` | REAL | 습도 |
| `dust_level` | TEXT | 좋음/보통/나쁨/매우나쁨 |
| `created_at` | TIMESTAMP | |

---

## email_log

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID PK | |
| `user_id` | TEXT | |
| `date` | DATE | 수신 날짜 |
| `sender` | TEXT | 발신자 |
| `subject` | TEXT | 제목 |
| `summary` | TEXT | GPT 요약 |
| `is_read` | BOOLEAN | 읽음 여부 |
| `uid` | TEXT | 이메일 UID (중복 방지) |
| `created_at` | TIMESTAMP | |

---

## RLS 정책

모든 테이블: `auth.uid()::text = user_id` 조건으로 본인 데이터만 접근 가능.
