# 🌧️ 먹구름 (mukgoorm)

디스코드에서 동작하는 1인 1캐릭터 라이프스타일 관리 멀티봇.  
음식을 입력하면 나만의 캐릭터에게 밥을 주는 행위로 연결되고,  
**칼로리·날씨·체중·이메일 정보를 수치가 아닌 캐릭터 이미지와 대사로 간접 전달**합니다.

> 현재 구현: **v3.2** | 목표 아키텍처: **v4.0** | 개발 브랜치: `develop`

---

## 🤖 멀티봇 구조

기능별로 독립된 봇 프로세스로 분리. 모든 봇이 **동일한 Supabase DB를 공유**하며, 봇 간 HTTP 통신 없이 DB가 단일 진실 공급원 역할을 합니다.

```
bot.py          먹구름봇     오케스트레이터 · 온보딩 · 설정 · 식사(텍스트) · 스케줄러 · 캐릭터 관리
bot_mail.py     메일봇       IMAP 1분 폴링 · 이메일 알림 · 발신자 관리
bot_meal.py     식사봇       사진 식사 감지 · GPT-4o Vision · 칼로리 분석
bot_weather.py  날씨봇       기상청 API · 미세먼지 · 기상 시간 자동 알림
bot_weight.py   체중관리봇   체중 기록 · 목표 달성 · 추이 관리     [skeleton]
bot_diary.py    일기봇       일기 작성 · 감정 분석                  [구상 단계]
bot_schedule.py 일정봇       일정 등록 · 알림 · 반복                [구상 단계]
                                         ↓
                                   Supabase DB (전체 공유)
```

---

## 🗣️ UX — 자연어 대화 방식 (v4.0)

유저가 전용 채널에서 자유롭게 채팅하면 먹구름봇이 의도를 분류해 해당 서브봇을 자동으로 트리거합니다.

```
유저 전용 채널 (#{이름}-채팅창)
┌─────────────────────────────────────────────────┐
│ [📌 고정] 캐릭터 상태 Embed + GPT 대사            │
│                                                 │
│ 유저: "나 오늘 점심에 비빔밥 먹었어"               │
│  → 먹구름봇: 의도 분류 → 식사봇 트리거              │
│  → 식사봇: 칼로리 분석 결과 Embed (직접 응답)       │
│                                                 │
│ 유저: (사진 첨부)                                │
│  → 식사봇: "음식 사진이에요? [✅ 분석] [❌ 아니야]" │
└─────────────────────────────────────────────────┘
```

### 자연어 트리거 목록

| 발화 예시 | 의도 | 처리 흐름 | 최종 응답 위치 |
|-----------|------|-----------|-----------|
| "점심에 비빔밥 먹었어" | meal | 메인봇 → 🍽️ 버튼 제공 → 클릭 후 Modal | 전용 채널 |
| 사진 직접 업로드 | meal_photo | 식사봇 on_message 감지 → Vision 분석 | 전용 채널 |
| "몸무게 68kg" | weight | task_queue → 체중봇 처리 → 메인봇 결과 수신 | 전용 채널 |
| "오늘 하루 적고 싶어" | diary | task_queue → 일기봇 처리 → 메인봇 결과 수신 | 전용 채널 |
| "다음 주 화요일 병원 예약" | schedule | task_queue → 일정봇 처리 → 메인봇 결과 수신 | 전용 채널 + 알림 쓰레드 (D-day Push) |

### 오케스트레이터 동작 원리

```
먹구름봇 on_message
  → [1단계] GPT-4o 의도 분류 (meal / diary / schedule / weight / none)
      → intent_log INSERT  ← ML 학습 데이터 축적

  [meal 감지]
      → 🍽️ 식사입력 버튼 전송 (task_queue 미사용)
      → 클릭 → 텍스트: MealInputModal / 사진: 식사봇 on_message 경로

  [diary / schedule / weight 감지]
      → task_queue INSERT { bot_target, user_id, payload, status: 'pending' }
      → 먹구름봇: done 항목 폴링 루프 대기

서브봇 폴링 루프 (5~30초)
  → task_queue SELECT (본인 항목, status = 'pending')
  → 처리 (GPT 파싱, DB 저장)
  → task_queue UPDATE { status: 'done', result_json: { ... } }

먹구름봇 done 폴링
  → result_json 파싱 → 결과 Embed 빌드
  → personal_channel_id에 결과 전송 + 캐릭터 Embed 갱신
  → task_queue status = 'archived'

  [2단계, v4.0 이후] ML 의도 분류기 (50건+ 누적 시)
    TF-IDF + LogisticRegression → GPT 의도 분류 대체
    GPT는 엔티티 추출만 담당 (비용 절감 + 개인화)
```

---

## 🏗️ 디스코드 채널 구조

```
서버
├── #먹구름-시작  (공용 — 온보딩 진입점)
│     [🐣 다마고치 시작하기] 버튼 고정
│
└── 📁 먹구름  (카테고리)
    │
    ├── #{이름}-채팅창  (유저A 전용 채널)
    │     캐릭터 상태 Embed 고정 · 자연어 대화 · 서브봇 직접 응답
    │   ├── 🔔 {이름}의 알림    ← Push 전용: 날씨 기상 알림, 일정 D-day
    │   └── 📧 {이름}의 메일함  ← Push 전용: 이메일 알림
    │
    └── #{이름}-채팅창  (유저B — 동일 구조)
```

> **Push vs 직접 응답 구분**  
> - 유저가 요청한 것 (식사·체중·일기 등) → 서브봇이 채널에 **직접 응답**  
> - 시스템 자동 알림 (날씨·일정·메일) → **Push 전용 쓰레드**로만 전송

### users 테이블 채널 컬럼

| 컬럼 | 역할 |
|------|------|
| `personal_channel_id` | 유저 전용 채널 (대화 + 서브봇 응답) |
| `info_thread_id` | Push 전용: 날씨 + 일정 알림 통합 |
| `mail_thread_id` | Push 전용: 메일봇 알림 |
| `thread_id` | v3.2 메인 쓰레드 (fallback 기준, 기존 유저 호환) |

---

## 📁 프로젝트 구조

```
mukgoorm/
├── bot.py              먹구름봇 — 오케스트레이터, 온보딩, 스케줄러
├── bot_mail.py         메일봇
├── bot_meal.py         식사봇
├── bot_weather.py      날씨봇
├── bot_weight.py       체중관리봇 (skeleton)
├── bot_diary.py        일기봇 (미구현)
├── bot_schedule.py     일정봇 (미구현)
│
├── cogs/
│   ├── onboarding.py       온보딩 — 전용 채널 + 알림/메일 쓰레드 2개 생성
│   ├── meal.py             사진 식사 감지 — personal_channel_id 직접 응답
│   ├── weather.py          날씨 연동 — info_thread_id Push 전용
│   ├── email_monitor.py    IMAP 폴링 — mail_thread_id Push 전용
│   ├── weight.py           체중 기록 Modal — personal_channel_id 직접 응답
│   ├── summary.py          하루 정리 Ephemeral
│   ├── settings.py         설정 하위 메뉴 (내정보/위치/시간/이메일)
│   ├── time_settings.py    시간 설정 Select Menu
│   └── scheduler.py        APScheduler (식사 알림 / 칼로리 판정 / 주간 리포트)
│
├── utils/
│   ├── db.py               Supabase CRUD 전체 (모든 봇 공유)
│   ├── gpt.py              GPT-4o 래퍼 (파싱 / Vision / 대사 / 요약)
│   ├── embed.py            메인 Embed UI + MealInputModal
│   ├── image.py            11종 이미지 우선순위 선택
│   ├── badges.py           배지 7종 + 달성 체크
│   ├── pattern.py          식습관 패턴 5종 분석
│   ├── ml.py               칼로리 보정 모델 (Ridge / RandomForest)
│   ├── gpt_ml_bridge.py    ML 결과 → GPT 프롬프트 브릿지
│   ├── nutrition.py        식약처 식품영양성분 DB API + GPT fallback
│   ├── mail.py             네이버 IMAP / SMTP 클라이언트
│   └── email_ui.py         이메일 공통 Modal
│
├── images/                 캐릭터 이미지 11종 (.png)
├── models/                 유저별 칼로리 보정 모델 (.pkl, 자동 생성)
├── docs/                   프로젝트 문서
├── .env
└── requirements.txt
```

---

## 🚀 실행 방법

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 프로젝트 루트에 배치

### 3. 봇 실행

```bash
python bot.py          # 터미널 1 — 먹구름봇 (온보딩 / 설정 / 스케줄러)
python bot_mail.py     # 터미널 2 — 메일봇 (IMAP 1분 폴링)
python bot_meal.py     # 터미널 3 — 식사봇 (사진 감지 / GPT Vision)
python bot_weather.py  # 터미널 4 — 날씨봇 (기상청 API / wake_time 알림)
```

### 4. 디스코드 최초 설정

```
!setup
```

→ `#먹구름-시작` 채널에 [🐣 다마고치 시작하기] 버튼 고정

---

## ⚙️ 환경변수 (.env)

| 변수명 | 설명 | 상태 |
|--------|------|------|
| `DISCORD_TOKEN` | 먹구름봇 토큰 | 필수 |
| `DISCORD_TOKEN_EMAIL` | 메일봇 토큰 | 필수 |
| `DISCORD_TOKEN_MEAL` | 식사봇 토큰 | 필수 |
| `DISCORD_TOKEN_WEATHER` | 날씨봇 토큰 | 필수 |
| `DISCORD_TOKEN_WEIGHT` | 체중관리봇 토큰 | 발급 필요 |
| `DISCORD_TOKEN_DIARY` | 일기봇 토큰 | 구현 후 필요 |
| `DISCORD_TOKEN_SCHEDULE` | 일정봇 토큰 | 구현 후 필요 |
| `OPENAI_API_KEY` | OpenAI API 키 | 필수 |
| `WEATHER_API_KEY` | 기상청 공공데이터 포털 인증키 | 필수 |
| `AIR_API_KEY` | 에어코리아 API 키 (미세먼지) | 필수 |
| `FOOD_API_KEY` | 식약처 식품영양성분 DB API 키 | 필수 |
| `DATABASE_URL` | Supabase Session pooler URL | 필수 |
| `TAMAGOTCHI_CHANNEL_ID` | 온보딩 진입점 채널 ID | 필수 |
| `TAMAGOTCHI_CATEGORY_ID` | 유저 전용 채널 카테고리 ID | 채널 구조 전환 시 |
| `N8N_FOOD_WEBHOOK_URL` | n8n 음식 추천 웹훅 URL | URL 수령 후 등록 |

> 이메일 수신 계정은 `.env`가 아닌 유저가 디스코드 `/이메일설정`으로 직접 입력.  
> → Supabase `users.naver_email / naver_app_pw`에 유저별 저장.

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| 디스코드 | discord.py 2.x (slash commands, View/Modal, on_message) |
| AI | OpenAI GPT-4o (자연어 파싱 · Vision · 의도 분류 · 대사 생성 · 이메일 요약) |
| 영양 DB | 식약처 식품영양성분 DB API (1순위) + GPT fallback |
| 날씨 | 기상청 공공데이터 API (초단기실황) |
| 미세먼지 | 에어코리아 API (PM10 · PM2.5) |
| 이메일 | 네이버 IMAP SSL |
| DB | Supabase (PostgreSQL) + psycopg2-binary Session pooler |
| 스케줄러 | APScheduler AsyncIOScheduler |
| ML | scikit-learn (Ridge · RandomForest · TF-IDF · LogisticRegression) |
| 칼로리 공식 | Mifflin-St Jeor BMR |
| 음식 추천 | n8n 웹훅 연동 (URL 수령 후 활성화) |

---

## 🤖 오픈소스 ML 모델

GPT 의존도를 점진적으로 줄이고 개인화를 높이기 위해 HuggingFace 공개 모델을 단계적으로 도입합니다.  
**"GPT가 초기 label 생성 → 데이터 축적 → 오픈소스 모델로 대체"** 패턴을 전 컴포넌트에 적용합니다.

### 의도 분류 — `klue/roberta-small`

> 한국어 자연어 발화를 5개 의도 클래스로 분류 (meal / diary / schedule / weight / none)

| 항목 | 내용 |
|------|------|
| 출처 | [huggingface.co/klue/roberta-small](https://huggingface.co/klue/roberta-small) |
| 개발 | KLUE (Korean Language Understanding Evaluation) 팀 |
| 기반 | RoBERTa — 한국어 전용 사전학습 |
| 크기 | 68M params (~260MB) |
| 추론 환경 | CPU 가능 (추론 1회 ~0.1~0.3초) |
| 적용 방식 | intent_log 50건+ 누적 후 fine-tuning, GPT 의도 분류 대체 |

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("klue/roberta-small")
model = AutoModelForSequenceClassification.from_pretrained(
    "klue/roberta-small", num_labels=5
)
```

---

### 감정 분석 — `tabularisai/multilingual-sentiment-analysis`

> 일기 텍스트에서 감정 극성(긍정/부정/중립)과 강도(1~5)를 추출

| 항목 | 내용 |
|------|------|
| 출처 | [huggingface.co/tabularisai/multilingual-sentiment-analysis](https://huggingface.co/tabularisai/multilingual-sentiment-analysis) |
| 기반 | DistilBERT multilingual — 17개 언어 지원 (한국어 포함) |
| 크기 | ~545MB |
| 추론 환경 | CPU 가능 |
| 출력 | Very Negative / Negative / Neutral / Positive / Very Positive → 강도 1~5 직접 매핑 |
| 적용 방식 | 일기봇 구현 시 GPT 감정 분석 대체 (fine-tuning 불필요, 즉시 사용) |

```python
from transformers import pipeline

classifier = pipeline(
    "text-classification",
    model="tabularisai/multilingual-sentiment-analysis"
)
result = classifier("오늘 너무 힘든 하루였다...")
# → [{'label': 'Very Negative', 'score': 0.87}]
```

---

### 이메일 요약 — `gogamza/kobart-summarization`

> 200자 초과 이메일 본문을 한국어로 요약

| 항목 | 내용 |
|------|------|
| 출처 | [huggingface.co/gogamza/kobart-summarization](https://huggingface.co/gogamza/kobart-summarization) |
| 개발 | SKT-AI KoBART 기반 fine-tuning |
| 기반 | KoBART — 한국어 뉴스/정보성 텍스트 요약 특화 |
| 크기 | ~500MB |
| 추론 환경 | CPU 가능 |
| 적용 방식 | 메일봇 리팩토링 시 GPT 요약 대체 (즉시 사용 가능) |

```python
from transformers import AutoTokenizer, BartForConditionalGeneration

tokenizer = AutoTokenizer.from_pretrained("gogamza/kobart-summarization")
model = BartForConditionalGeneration.from_pretrained("gogamza/kobart-summarization")

inputs = tokenizer(email_body, return_tensors="pt", max_length=512, truncation=True)
summary_ids = model.generate(inputs["input_ids"], max_length=64)
summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
```

---

### 칼로리 보정 — `scikit-learn Ridge / RandomForest`

> 유저별 식사 기록을 기반으로 칼로리 추정값을 개인화 보정

| 항목 | 내용 |
|------|------|
| 출처 | [scikit-learn.org](https://scikit-learn.org) |
| 방식 | 유저별 독립 모델 (`models/calorie_model_{user_id}.pkl`) |
| 전환 조건 | 30건 미만: Ridge (안정적) → 30건 이상: RandomForest (비선형 패턴) |
| 적용 방식 | 전용 오픈소스 모델 없음 — GPT 추정값이 초기 label, 유저 데이터로 지속 재학습 |

---

### GPT → 오픈소스 전환 로드맵

```
현재 (v3.2)          →   도입 시점
─────────────────────────────────────────────────────
GPT 칼로리 추정       →   scikit-learn 보정 (✅ 운영 중)
GPT 의도 분류         →   klue/roberta-small (intent_log 50건+ 이후)
GPT 감정 분석         →   tabularisai (일기봇 구현 시 즉시)
GPT 이메일 요약       →   kobart-summarization (메일봇 리팩토링 시)
```

> 모델 동시 로드 시 총 메모리 약 2.5~3GB. 서버 RAM 4GB 이상 권장.  
> on-demand 로드(사용 시에만 메모리에 올림)로 운용하면 2GB 이하로 관리 가능.

---

## 📊 칼로리 분석 우선순위

```
1순위: 식약처 식품영양성분 DB API  → 공식 영양 수치
         ↓ 실패 시
2순위: OpenAI GPT-4o fallback     → 추정 칼로리/영양소
         ↓ 항상 적용
3순위: ML 보정 (get_corrected_calories)
         · 즉시: 양 표현 키워드 배율 (조금 ×0.7 / 많이 ×1.4 / 두 그릇 ×2.0)
         · 30건+ 누적: Ridge / RandomForest 개인화 모델 추가 보정
```

---

## ⏱️ 스케줄러 동작 요약

| 시각 | 담당 봇 | 동작 |
|------|---------|------|
| 매 1분 | 메일봇 | IMAP 폴링 → 새 메일 `mail_thread_id` 알림 |
| 유저 wake_time | 날씨봇 | 기상청·에어코리아 → `info_thread_id` 날씨 Embed |
| 식사시간 -30분 | 먹구름봇 | 채널에 배고픔 예고 메시지 |
| 식사시간 정각 | 먹구름봇 | 미입력 시 upset.png + GPT 대사 |
| 식사시간 +1시간 | 먹구름봇 | 미입력 시 추가 GPT 대사 |
| 매 시간 정각 | 먹구름봇 | 전체 유저 hunger -5 |
| 매일 22:00 | 먹구름봇 | 칼로리 판정 + 스트릭 갱신 + 배지 체크 |
| 매주 일요일 03:00 | 먹구름봇 | ML 칼로리 보정 모델 전체 재학습 |
| 매주 일요일 08:00 | 먹구름봇 | 주간 리포트 (칼로리·끼니·체중·스트릭·배지) |

---

## 🖼️ 캐릭터 이미지 (11종, 우선순위 순)

| 이미지 | 표시 조건 | 우선순위 |
|--------|-----------|---------|
| `cheer.png` | 목표 달성 / 배지 획득 | 1 |
| `eat.png` | 식사 입력 직후 3분 | 2 |
| `upset.png` | 배고픔 (hunger < 40) | 3 |
| `wear_mask.png` | PM10 > 80 또는 PM2.5 > 35 | 4 |
| `rainy.png` | 비 / 소나기 | 4 |
| `snow.png` | 눈 | 4 |
| `hot.png` | 기온 ≥ 26°C | 4 |
| `warm.png` | 기온 ≤ 5°C | 4 |
| `tired.png` | hp < 40 또는 mood < 40 | 5 |
| `smile.png` | 상태 양호 (hp·hunger·mood ≥ 70) | 5 |
| `normal.png` | 기본값 | 5 |

> hp / hunger / mood 수치는 내부 전용 — 유저에게 직접 노출하지 않습니다.

---

## 🏅 도전과제 배지 (7종)

| 배지 ID | 이름 | 달성 조건 |
|---------|------|----------|
| `first_meal` | 🍽️ 첫 끼니 | 첫 번째 식사 기록 |
| `streak_3` | 🔥 3일 연속 | 3일 연속 식사 기록 |
| `streak_7` | 🌟 일주일 달인 | 7일 연속 |
| `streak_30` | 👑 한 달 챔피언 | 30일 연속 |
| `calorie_10` | 🎯 목표 달성 10회 | 목표 칼로리 ≥ 90% 달성일 10일 이상 |
| `photo_10` | 📸 사진 마스터 | 사진 입력 누적 10회 이상 |
| `morning_7` | 🌅 아침형 인간 | 아침 끼니 누적 기록 7회 이상 |

---

## 🗄️ DB 테이블 요약

| 테이블 | 소유 봇 | 주요 내용 |
|--------|---------|----------|
| `users` | 공통 | 유저 정보, 시간 설정, 채널/쓰레드 ID, 이메일 자격증명 |
| `tamagotchi` | 먹구름봇 | hp / hunger / mood / 현재 이미지 |
| `meals` | 먹구름봇(텍스트) + 식사봇(사진) | 식사 기록, 칼로리, 영양소 |
| `weather_log` | 날씨봇 | 날씨·기온·미세먼지 기록 |
| `weight_log` | 체중관리봇 | 체중 기록 |
| `email_senders` | 메일봇 | 발신자 화이트리스트 |
| `email_log` | 메일봇 | 수신 이메일 로그 |
| `task_queue` | 먹구름봇 | 봇 간 단방향 트리거 (오케스트레이터 → 서브봇) |
| `intent_log` | 먹구름봇 | 자연어 의도 분류 ML 학습 데이터 |
| `diary_log` | 일기봇 (예정) | 일기 원문 + 감정 분석 |
| `schedules` | 일정봇 (예정) | 일정·반복·알림 상태 |

상세: [`docs/03_DATABASE.md`](docs/03_DATABASE.md)

---

## 📧 이메일 모니터링

| 항목 | 내용 |
|------|------|
| 처리 봇 | 메일봇 (bot_mail.py) |
| 폴링 간격 | 1분 |
| 지원 메일 | 네이버 IMAP SSL (imap.naver.com:993) |
| 스팸 필터 | 1단계: INBOX 한정 / 2단계: 제목 키워드 / 3단계: 발신자 화이트리스트 |
| 본문 처리 | ≤200자 → 원문 / >200자 → GPT-4o 요약 |
| 알림 위치 | `mail_thread_id` (Push 전용 쓰레드) |
| 슬래시 커맨드 | `/이메일설정` `/발신자추가` `/발신자목록` `/발신자삭제` |

---

## 🗺️ 개발 로드맵

| Phase | 버전 | 내용 |
|-------|------|------|
| ✅ 완료 | v1.0~v3.2 | 멀티봇 4개 운영, ML 칼로리 보정, 배지/스트릭, 이메일 모니터링 |
| 다음 | v3.3 | 체중관리봇 분리 + n8n 음식 추천 연동 |
| 예정 | v3.4 | 일기봇 — 감정 분석, 주간 감정 리포트 |
| 예정 | v3.5 | 일정봇 — 일정 등록, APScheduler 알림 |
| 장기 | v4.0 | 유저별 전용 채널 전환 + 자연어 오케스트레이터 + ML 의도 분류기 |

상세: [`docs/PRODUCTION_ROADMAP.md`](docs/PRODUCTION_ROADMAP.md)

---

## 📖 상세 문서

| 문서 | 내용 |
|------|------|
| [`docs/01_OVERVIEW.md`](docs/01_OVERVIEW.md) | 개요 · 기술스택 · 멀티봇 구조 |
| [`docs/02_FLOWS.md`](docs/02_FLOWS.md) | 전체 기능 흐름 (봇별 처리 주체 명시) |
| [`docs/03_DATABASE.md`](docs/03_DATABASE.md) | DB 스키마 · 테이블 소유권 |
| [`docs/05_ML_MODULES.md`](docs/05_ML_MODULES.md) | ML 모듈 · 의도 분류기 설계 |
| [`docs/06_PROGRESS.md`](docs/06_PROGRESS.md) | 구현 현황 · 이전 예정 · 버그 목록 |
| [`docs/PRODUCTION_ROADMAP.md`](docs/PRODUCTION_ROADMAP.md) | 전체 Phase 제작 순서 |
| [`docs/TEAM_OVERVIEW.md`](docs/TEAM_OVERVIEW.md) | 팀 기술 개요서 |
| [`docs/bots/00_INDEX.md`](docs/bots/00_INDEX.md) | 봇별 상세 문서 인덱스 |

---

현재 구현: **v3.2** | 목표 아키텍처: **v4.0** (2026-04-14)
