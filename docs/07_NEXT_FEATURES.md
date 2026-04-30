# 기능 개발 계획 — React 웹앱 기준

> last_updated: 2026-04-30 | 브랜치: `feat/web-migration`

---

## 아키텍처 개요

```
React 웹앱 (메인 UI)
  │
  ├── Supabase Auth + DB     — 인증 · 데이터 (기존 스키마 재활용)
  ├── OpenAI GPT-4o-mini     — 대화 · 분석 · 대사
  ├── n8n                    — ML · 자동화 · 이메일 IMAP · 음식 추천
  └── 알림 레이어
        ├── Discord Webhook  — 리포트 · 일정 Push
        └── 이메일 SMTP      — 리포트 발송 (선택)
```

---

## 기능 1 — 캐릭터 상태 (메인 화면)

**핵심 원칙:** hp/hunger/mood 수치 직접 노출 금지. 이미지+대사로만.

### 컴포넌트 구조

```typescript
// src/components/CharacterCard.tsx
// ─ 이미지 선택 로직 (11종, 날씨·hunger·mood 조합)
// ─ GPT-4o-mini 대사 생성
// ─ 캐릭터 상태 자동 갱신 (식사·체중 기록 시)
```

### 이미지 선택 로직 (Python → JS 변환)

```typescript
// utils/image.py → src/lib/image.ts
function selectCharacterImage(
  weather: string,
  hunger: number,  // 외부 노출 X, 내부 계산용
  mood: number,
  hp: number
): string {
  // 11종 이미지 우선순위 로직
  // 날씨봇 기상 시간 → 이미지 자동 교체 포함
}
```

---

## 기능 2 — 식사 기록

### 텍스트 입력 흐름

```
유저 텍스트 입력
  → 식약처 API 칼로리 조회 (1순위)
  → GPT-4o-mini 칼로리 추정 fallback (2순위)
  → meal_log 저장
  → hp/hunger 업데이트
  → 캐릭터 상태 갱신 + GPT 대사
```

### 사진 입력 흐름

```
사진 파일 업로드
  → base64 변환
  → GPT-4o-mini Vision 분석
  → 음식명 + 칼로리 추정
  → 확인 UI → meal_log 저장
```

### ML 연동 (n8n)

```
식사 기록 → intent_log 저장 (학습 데이터 축적)
  → 50건+ 누적 → n8n ML 모델 학습
  → 이후: ML이 의도 분류, GPT는 엔티티 추출만
```

---

## 기능 3 — 체중 관리

### 기능 목록

```
[ ] 체중 기록 (kg 입력)
[ ] 최근 14일 추이 그래프 (recharts LineChart)
[ ] 목표 체중 기준선 표시
[ ] 목표 달성 알림
[ ] 칼로리 목표 자동 조정 제안
    ─ 14일 추이 분석 → 감량/유지/증량 방향 제안
```

### 칼로리 공식

Mifflin-St Jeor (Python 봇과 동일):

```typescript
function calcBMR(gender: string, weight: number, height: number, age: number) {
  if (gender === 'male') return 10 * weight + 6.25 * height - 5 * age + 5
  return 10 * weight + 6.25 * height - 5 * age - 161
}
```

---

## 기능 4 — 날씨

### 데이터 소스

- 기상청 공공데이터 API (초단기실황조회)
- 에어코리아 API (PM10, PM2.5)

### 흐름

```
기상 시간 도달 (APScheduler → 웹앱에서는 useEffect + interval)
  → 기상청 API 호출
  → 날씨 상태 분류
  → 캐릭터 이미지 자동 교체 (별도 알림 없음 — 핵심 원칙 유지)
  → 미세먼지 → 캐릭터 대사에 간접 반영
```

> **핵심 원칙:** 날씨는 별도 알림 없음. 기상 시간에 이미지 교체로만 전달.

---

## 기능 5 — 일정 관리

**Python 봇에서 구상 단계 → 웹앱에서 실제 구현**

### 기능 목록

```
[ ] 일정 등록 (제목, 날짜/시간, 반복 여부)
[ ] 일정 목록 뷰
[ ] D-day 표시
[ ] 알림
    ─ 브라우저 Notification API (웹앱 열려 있을 때)
    ─ Discord Webhook (앱 닫혀 있을 때)
[ ] 반복 일정 (매일/매주/매월)
```

### DB (기존 schedules 테이블 재활용)

```sql
CREATE TABLE IF NOT EXISTS schedules (
  schedule_id  SERIAL PRIMARY KEY,
  user_id      TEXT,
  title        TEXT,
  scheduled_at TIMESTAMP,
  repeat_type  TEXT DEFAULT 'none',  -- none/daily/weekly/monthly
  notified     BOOLEAN DEFAULT FALSE,
  created_at   TIMESTAMP DEFAULT NOW()
);
```

---

## 기능 6 — 일기 + 감정 분석

**Python 봇에서 구상 단계 → 웹앱에서 실제 구현**

### 기능 목록

```
[ ] 일기 작성 (textarea, 날짜별 1개)
[ ] GPT-4o-mini 감정 분석 → 키워드 + 감정 레이블
[ ] 주간 감정 추이 차트 (recharts)
[ ] diary_log 저장
```

### DB (기존 diary_log 테이블 재활용)

```sql
CREATE TABLE IF NOT EXISTS diary_log (
  log_id     SERIAL PRIMARY KEY,
  user_id    TEXT,
  content    TEXT,
  emotion    TEXT,
  keywords   TEXT,
  written_at TIMESTAMP DEFAULT NOW()
);
```

---

## 기능 7 — 이메일 모니터링

**Python 봇에서 구현됨 → 웹앱에서는 n8n이 서버사이드 처리**

### 흐름

```
n8n Cron (1분)
  → 네이버 IMAP 폴링
  → 새 메일 감지
  → Supabase email_log 저장
  → Supabase Realtime → 웹앱 실시간 반영
  → 사이드바 빨간 점 알림 표시
```

> 브라우저에서 IMAP 직접 접근 불가 → n8n 서버사이드 처리 필수.

### 기능 목록

```
[ ] 이메일 목록 뷰 (읽음/안읽음)
[ ] 발신자 관리 (화이트리스트)
[ ] 스팸 필터 (GPT-4o-mini 분류)
[ ] 실시간 새 메일 알림 (사이드바 빨간 점)
```

---

## 기능 8 — 주간 리포트

**Discord 임베드 한계 해소 → CSS 풀 커스텀 리포트 페이지**

### 리포트 구성

```
/report 페이지
  ├── 이번 주 총 칼로리 vs 목표
  ├── 일별 칼로리 바 차트
  ├── 체중 변화 (주간)
  ├── 감정 추이 (주간)
  ├── 스트릭 현황
  └── 배지 달성 현황 (7종)
```

### 발송 옵션

```
[ ] Discord Webhook (임베드 요약 + 리포트 링크)
[ ] 이메일 SMTP (n8n 워크플로우)
    ─ HTML 이메일로 리포트 풀 내용 발송
```

---

## 기능 9 — 음식 추천 (n8n)

**n8n 워크플로우 이미 구성됨. 웹훅 URL 수령 후 즉시 연결 가능.**

### 흐름

```
유저 요청 (잔여 칼로리 기반 버튼 또는 자동 제안)
  → VITE_N8N_FOOD_WEBHOOK_URL POST
  → n8n: 주소 기반 주변 식당 검색 + 잔여 칼로리 고려
  → 추천 결과 반환
  → 음식 추천 UI 표시
```

### 트리거 방식 (결정 필요)

```
[ ] A. 식사 기록 후 잔여 칼로리 기반 자동 제안
[ ] B. "음식 추천" 버튼 클릭
[ ] C. 자연어 입력 감지 (ML 의도 분류 연동)
```

---

## ML 의도 분류 (n8n 파이프라인)

### 단계별 전환

```
초기: GPT-4o-mini 의도 분류
  → intent_log 저장 (user_id, message, intent, entity_json)

이후: ML 모델 학습 (n8n 처리)
  → 유저별 50건+ 누적 → TF-IDF + LogisticRegression 학습
  → ML이 의도 분류 → GPT는 엔티티 추출만
  → GPT 비용 절감 + 개인화
```

### intent_log 테이블

```sql
CREATE TABLE IF NOT EXISTS intent_log (
  log_id        SERIAL PRIMARY KEY,
  user_id       TEXT NOT NULL,
  message       TEXT NOT NULL,
  intent        TEXT NOT NULL,  -- meal/weight/diary/schedule/email/none
  entity_json   TEXT,
  classified_by TEXT DEFAULT 'gpt',  -- 'gpt' | 'ml'
  created_at    TIMESTAMP DEFAULT NOW()
);
```

---

## 사이드바 UI — 기능별 알림 표시

Discord 쓰레드 분리 목적(기능별 메시지 구분)을 웹앱 사이드바로 대체.

```
사이드바
├── 🏠 홈 (캐릭터 상태)
├── 🍽️ 식사 기록          ← 오늘 입력 안 했으면 빨간 점
├── ⚖️ 체중 관리
├── 🌤️ 날씨
├── 📅 일정               ← 오늘 일정 있으면 빨간 점
├── 📔 일기               ← 오늘 입력 안 했으면 빨간 점
├── 📧 이메일              ← 새 메일 있으면 빨간 점
├── 📊 주간 리포트
└── ⚙️ 설정
```
