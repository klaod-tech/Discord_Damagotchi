# 다음 작업 목록 — React 웹앱 전환

> 기준: 2026-04-30 | 브랜치: `feat/web-migration`

---

## 작업 순서 개요

```
1단계  React 기본 세팅          ← 지금 여기
2단계  인증 · 온보딩
3단계  핵심 기능 (식사·체중·날씨)
4단계  확장 기능 (일정·일기·이메일)
5단계  n8n 연동
6단계  알림 · 주간 리포트
```

---

## 1단계 — React 기본 세팅

### SETUP-1. Vite + React + TypeScript 프로젝트 초기화

```bash
npm create vite@latest mukgoorm-web -- --template react-ts
cd mukgoorm-web
npm install
```

**추가 설치 패키지:**

```bash
npm install @supabase/supabase-js     # Supabase 클라이언트
npm install react-router-dom          # 라우팅
npm install openai                    # GPT API
npm install axios                     # HTTP 클라이언트 (n8n 웹훅 호출)
npm install recharts                  # 체중 추이 그래프
npm install react-query               # 서버 상태 관리
```

### SETUP-2. Supabase 연결 설정

```typescript
// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseKey)
```

**환경변수 (.env.local):**

```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_OPENAI_API_KEY=
VITE_WEATHER_API_KEY=
VITE_FOOD_API_KEY=
VITE_N8N_FOOD_WEBHOOK_URL=
VITE_DISCORD_WEBHOOK_URL=
```

### SETUP-3. 라우팅 구조

```
/                 → 캐릭터 상태 메인 화면
/login            → 로그인
/onboarding       → 온보딩 (최초 1회)
/meal             → 식사 기록
/weight           → 체중 관리
/weather          → 날씨
/schedule         → 일정
/diary            → 일기
/email            → 이메일 모니터링
/report           → 주간 리포트
/settings         → 설정
```

### SETUP-4. 기본 레이아웃 컴포넌트

```
src/
├── components/
│   ├── Layout.tsx          — 사이드바 + 메인 영역
│   ├── Sidebar.tsx         — 기능별 네비게이션 (빨간 점 알림 표시)
│   └── CharacterCard.tsx   — 캐릭터 이미지 + GPT 대사
├── pages/
│   ├── Home.tsx
│   ├── Meal.tsx
│   ├── Weight.tsx
│   ├── Weather.tsx
│   ├── Schedule.tsx
│   ├── Diary.tsx
│   ├── Email.tsx
│   ├── Report.tsx
│   └── Settings.tsx
├── lib/
│   ├── supabase.ts
│   ├── openai.ts
│   └── n8n.ts
└── hooks/
    ├── useUser.ts
    ├── useMeals.ts
    └── useCharacter.ts
```

---

## 2단계 — 인증 · 온보딩

### AUTH-1. Supabase Auth 이메일 로그인

```typescript
// src/lib/auth.ts
import { supabase } from './supabase'

export async function signIn(email: string, password: string) {
  return supabase.auth.signInWithPassword({ email, password })
}

export async function signUp(email: string, password: string) {
  return supabase.auth.signUp({ email, password })
}

export async function signOut() {
  return supabase.auth.signOut()
}
```

### AUTH-2. 온보딩 플로우

**수집 정보 (기존 DB 스키마 재활용):**

```
1. 이름 (display_name)
2. 도시 (city) — 날씨 API용
3. 동 단위 주소 (address) — 음식 추천용
4. 성별 (gender)
5. 나이 (age)
6. 키 (height)
7. 목표 체중 (goal_weight)
8. 기상 시간 (wake_time)
9. 취침 시간 (sleep_time)
```

**온보딩 완료 후:**
- `users` 테이블에 유저 프로필 저장
- 캐릭터 이미지 초기화 (neutral 상태)
- 메인 화면으로 이동

---

## 3단계 — 핵심 기능

### MEAL-1. 식사 기록 (텍스트)

**Python 변환 대상:** `cogs/meal.py`, `utils/nutrition.py`

```typescript
// src/lib/meal.ts
async function analyzeMeal(text: string, userId: string) {
  // 1. 식약처 API 칼로리 조회
  // 2. fallback: GPT-4o-mini 칼로리 추정
  // 3. Supabase meal_log 저장
  // 4. hp/hunger 업데이트
}
```

### MEAL-2. 식사 기록 (사진)

```typescript
// GPT-4o-mini Vision 활용
async function analyzeMealPhoto(imageFile: File, userId: string) {
  // 1. 이미지 → base64
  // 2. GPT-4o-mini Vision 분석
  // 3. 칼로리 추정 + meal_log 저장
}
```

### WEIGHT-1. 체중 기록 + 추이 그래프

**Python 변환 대상:** `cogs/weight.py`

```typescript
// recharts LineChart 활용
// 최근 14일 체중 추이
// 목표 체중 기준선 표시
```

### WEATHER-1. 날씨 표시

**Python 변환 대상:** `cogs/weather.py`, `utils/image.py`

```typescript
// 기상청 API → 날씨 상태
// 날씨 상태 → 캐릭터 이미지 선택 로직 (11종)
// 기상 시간에 자동 반영
```

---

## 4단계 — 확장 기능

### SCHEDULE-1. 일정 관리

**Python 변환 대상:** `docs/bots/schedule/` (구상 단계 → 웹앱에서 구현)

```typescript
// 일정 등록 (제목, 날짜, 반복 여부)
// 알림: 브라우저 Notification API + Discord Webhook
// 일정 목록 뷰
```

### DIARY-1. 일기 + 감정 분석

**Python 변환 대상:** `docs/bots/diary/` (구상 단계 → 웹앱에서 구현)

```typescript
// 일기 작성 (textarea)
// GPT-4o-mini 감정 분석
// 주간 감정 추이 차트
```

### EMAIL-1. 이메일 모니터링

**Python 변환 대상:** `cogs/email_monitor.py`, `utils/mail.py`

```
주의: 네이버 IMAP은 서버사이드에서만 접근 가능.
→ Supabase Edge Function 또는 n8n 워크플로우로 처리.
→ n8n이 IMAP 폴링 → 새 메일 → Supabase DB 저장 → 웹앱 실시간 조회.
```

---

## 5단계 — n8n 연동

### N8N-1. ML 의도 분류 파이프라인

```
웹앱 → n8n 웹훅 → ML 모델 → 의도 분류 결과 반환
                  ↕ (학습 데이터 축적)
              intent_log (Supabase)
```

**초기 (GPT 라벨링):**
- 유저 입력 → GPT-4o-mini 의도 분류
- 결과 + 원문 → intent_log 저장

**이후 (ML 전환):**
- 50건+ 누적 → n8n에서 ML 모델 학습
- ML 모델이 의도 분류 → GPT는 엔티티 추출만

### N8N-2. 음식 추천

```typescript
// src/lib/n8n.ts
async function requestFoodRecommendation(
  userId: string,
  address: string,
  calRemaining: number,
  mood: string = ''
) {
  const res = await axios.post(import.meta.env.VITE_N8N_FOOD_WEBHOOK_URL, {
    user_id: userId,
    address,
    cal_remaining: calRemaining,
    mood,
  })
  return res.data
}
```

### N8N-3. 이메일 모니터링 워크플로우

```
n8n Cron (1분) → 네이버 IMAP 폴링 → 새 메일 감지
  → Supabase email_log 저장
  → 웹앱 실시간 반영 (Supabase Realtime)
```

---

## 6단계 — 알림 · 주간 리포트

### REPORT-1. 주간 리포트 CSS 뷰

```
기존 Discord 임베드 → 웹앱 내 전용 리포트 페이지 (/report)
  ─ 주간 칼로리 차트
  ─ 체중 변화
  ─ 감정 추이
  ─ 스트릭 + 배지
```

### NOTIFY-1. Discord Webhook 발송

```typescript
// src/lib/discord.ts
async function sendToDiscord(webhookUrl: string, content: object) {
  await axios.post(webhookUrl, content)
}

// 주간 리포트: Discord Embed 형식으로 발송
// 일정 알림: 단순 텍스트 또는 Embed
```

### NOTIFY-2. 브라우저 Push 알림 (PWA)

```typescript
// 일정 알림: Notification API
// 서비스 워커 등록 → 백그라운드 알림 가능
// 향후 Electron 패키징 시 OS 네이티브 알림으로 전환
```

---

## 미결 사항

```
[ ] Supabase RLS 정책 설계 (유저별 데이터 격리)
[ ] 이미지 생성 (NovelAI) 서버사이드 처리 방법
    → Supabase Edge Function / n8n 워크플로우
[ ] 이메일 모니터링 IMAP 처리 위치 확정 (Edge Function vs n8n)
[ ] PWA vs Electron 패키징 방향 결정
[ ] Discord Webhook URL 수령
```

---

## 레거시 Python 봇 버그 (웹앱 전환 시 불필요)

기존 NEXT.md의 Python 봇 버그 수정 항목들은 웹앱 전환으로 자동 해소됨.  
Python 봇은 `develop` 브랜치에 보존. 웹앱 완성 후 아카이브.
