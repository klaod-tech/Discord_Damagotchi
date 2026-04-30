# 전환 계획서 — Python Discord 봇 → React 웹앱

> 작성일: 2026-04-30  
> 브랜치: `feat/web-migration`  
> 목적: Discord 봇의 구조적 한계를 해소하고 React 웹앱으로 전환하는 로드맵

---

## 전환 배경 요약

| 문제 | Discord 봇 한계 | 웹앱 해결 |
|------|----------------|----------|
| 프라이버시 | 관리자가 모든 유저 쓰레드 열람 가능. Discord 구조상 막을 수 없음 | Supabase Auth RLS — 유저별 완전 격리 |
| 디자인 | 임베드 커스텀 불가, 이모티콘 외 표현 한계 | CSS 자유 활용 |
| 리포트 | Discord 임베드 주간 리포트 가독성 최악 | 전용 리포트 페이지 (HTML/CSS) |
| 확장성 | 버튼/Modal UX 한계, 기능 추가마다 Cog 분리 필요 | 웹 라우팅 기반 자유로운 페이지 구성 |
| 배포 | Discord 앱 설치 필요 | 브라우저 접속, 향후 Electron 옵션 |

---

## Phase 1 — React 기본 세팅 (현재)

### 목표
웹앱 개발 환경 구축 + Supabase 연결 + 기본 레이아웃

### 체크리스트

```
[ ] Vite + React + TypeScript 초기화
[ ] Supabase client 연결 (src/lib/supabase.ts)
[ ] 환경변수 구성 (.env.local)
[ ] react-router-dom 라우팅 구조
[ ] 기본 레이아웃 (사이드바 + 메인 영역)
[ ] Supabase Auth 이메일 로그인
[ ] 온보딩 플로우 (유저 프로필 등록)
```

### 파일 구조 목표

```
mukgoorm-web/
├── src/
│   ├── components/
│   │   ├── Layout.tsx
│   │   ├── Sidebar.tsx
│   │   └── CharacterCard.tsx
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Meal.tsx
│   │   ├── Weight.tsx
│   │   ├── Weather.tsx
│   │   ├── Schedule.tsx
│   │   ├── Diary.tsx
│   │   ├── Email.tsx
│   │   ├── Report.tsx
│   │   └── Settings.tsx
│   ├── lib/
│   │   ├── supabase.ts
│   │   ├── openai.ts
│   │   └── n8n.ts
│   └── hooks/
│       ├── useUser.ts
│       ├── useMeals.ts
│       └── useCharacter.ts
├── .env.local
└── package.json
```

---

## Phase 2 — 인증 + 핵심 기능

### 목표
유저 인증 완성 + 식사·체중·날씨 핵심 기능 JavaScript 변환

### Python → JavaScript 변환 대상

| Python 파일 | JS 변환 대상 | 우선순위 |
|------------|------------|---------|
| `cogs/meal.py` | `src/lib/meal.ts` + `src/pages/Meal.tsx` | ★★★ |
| `utils/nutrition.py` | `src/lib/nutrition.ts` (식약처 API) | ★★★ |
| `cogs/weight.py` | `src/lib/weight.ts` + `src/pages/Weight.tsx` | ★★★ |
| `cogs/weather.py` | `src/lib/weather.ts` + `src/pages/Weather.tsx` | ★★ |
| `utils/image.py` | `src/lib/image.ts` (11종 이미지 선택 로직) | ★★ |
| `utils/gpt.py` | `src/lib/openai.ts` (GPT 래퍼) | ★★★ |
| `utils/db.py` | `src/lib/db.ts` (Supabase CRUD) | ★★★ |

### 체크리스트

```
[ ] Supabase Auth RLS 정책 설정 (유저별 데이터 격리)
[ ] useUser hook (유저 프로필 조회/수정)
[ ] 식사 기록 — 텍스트 입력 + 식약처 API + GPT fallback
[ ] 식사 기록 — 사진 입력 + GPT-4o-mini Vision
[ ] 체중 기록 + 추이 그래프 (recharts)
[ ] 날씨 — 기상청 API + 캐릭터 이미지 선택 로직
[ ] 캐릭터 상태 — hp/hunger/mood → 이미지+대사 (핵심 원칙 유지)
[ ] GPT 대사 생성 (openai.ts)
```

---

## Phase 3 — 확장 기능

### 목표
일정·일기·이메일 기능 웹앱 구현 (Python 봇에서 미구현이었던 기능들)

### 체크리스트

```
[ ] 일정 — 등록·목록·삭제 (schedules 테이블 재활용)
[ ] 일정 — 브라우저 Notification API 알림
[ ] 일기 — 작성 + GPT-4o-mini 감정 분석
[ ] 일기 — 주간 감정 추이 차트 (recharts)
[ ] 이메일 모니터링 — n8n IMAP 폴링 → Supabase Realtime 연동
[ ] 이메일 — 발신자 관리 (화이트리스트)
```

---

## Phase 4 — n8n 연동

### 목표
ML 파이프라인 + 음식 추천 + 이메일 자동화 n8n 연결

### 체크리스트

```
[ ] n8n 음식 추천 웹훅 URL 수령 + 환경변수 등록
[ ] src/lib/n8n.ts — 음식 추천 요청 함수
[ ] 음식 추천 UI (잔여 칼로리 기반 버튼 또는 자동 제안)
[ ] ML 의도 분류 파이프라인 n8n 연결
    ─ GPT 라벨링 → intent_log 저장 (데이터 축적)
    ─ 50건+ 누적 시 ML 모델 전환
[ ] 이메일 모니터링 n8n 워크플로우 연결
```

---

## Phase 5 — 알림 · 주간 리포트

### 목표
주간 리포트 CSS 뷰 + Discord Webhook + 이메일 발송

### 체크리스트

```
[ ] 주간 리포트 페이지 (/report) — CSS 풀 커스텀
    ─ 주간 칼로리 차트
    ─ 체중 변화
    ─ 감정 추이
    ─ 스트릭 + 배지 7종
[ ] Discord Webhook 발송 (src/lib/discord.ts)
[ ] 이메일 발송 옵션 (n8n SMTP 워크플로우)
[ ] 브라우저 Push 알림 (PWA Service Worker)
```

---

## Phase 6 — 마무리 (선택)

```
[ ] PWA 설정 (manifest.json, service worker)
    ─ 모바일 홈 화면 추가 가능
    ─ 오프라인 기본 지원
[ ] Electron 패키징 (exe 데스크톱 앱)
    ─ 백그라운드 실행
    ─ OS 네이티브 알림
    ─ 시스템 트레이
```

---

## 레거시 Python 봇 처리

| 시점 | 처리 방법 |
|------|----------|
| 웹앱 Phase 2 완료 | Python 봇 `develop` 브랜치 보존, 신규 개발 중단 |
| 웹앱 Phase 5 완료 | Python 봇 아카이브 태그 (`v3.2-legacy`) 추가 |
| 웹앱 안정화 | Python 봇 README에 "deprecated" 표기 |

---

## 미결 사항

```
[ ] Supabase RLS 정책 설계 (어느 테이블에 어떤 정책?)
[ ] NovelAI 이미지 생성 서버사이드 처리
    → Supabase Edge Function 또는 n8n 워크플로우
[ ] 네이버 IMAP 서버사이드 처리 위치
    → n8n 권장 (IMAP은 브라우저에서 직접 접근 불가)
[ ] Discord Webhook URL 수령
[ ] n8n 서버 위치 (로컬 vs 클라우드 n8n)
```
