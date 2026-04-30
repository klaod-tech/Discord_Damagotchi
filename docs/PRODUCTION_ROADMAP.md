# 먹구름 전체 제작 로드맵

> last_updated: 2026-04-30 | 전환 방향: Python Discord 봇 → React 웹앱

---

## 현재 상태 한눈에 보기

| 항목 | 상태 |
|------|------|
| Python 봇 (v3.2) | `develop` 브랜치 보존, 신규 개발 중단 |
| React 웹앱 | `feat/web-migration` 브랜치 — Phase 1 진행 중 |
| Supabase DB | 기존 스키마 재활용 (마이그레이션 불필요) |
| n8n | 워크플로우 구성됨, 웹훅 URL 수령 후 연결 |

---

## Phase 1 — React 기본 세팅 + 인증

**목표:** 웹앱 개발 환경 구축, Supabase 연결, 온보딩

```
[ ] Vite + React + TypeScript 프로젝트 초기화
[ ] Supabase client 연결
[ ] 환경변수 구성 (.env.local)
[ ] react-router-dom 라우팅 구조 (9개 페이지)
[ ] 기본 레이아웃 (사이드바 + 메인 영역)
[ ] Supabase Auth 이메일 로그인 / 회원가입
[ ] 온보딩 플로우 (이름·도시·주소·신체정보·시간 등록)
[ ] Supabase RLS 정책 (유저별 데이터 완전 격리)
```

---

## Phase 2 — 핵심 기능 JavaScript 변환

**목표:** 식사·체중·날씨·캐릭터 기능 웹앱 구현

```
[ ] GPT-4o-mini 래퍼 (src/lib/openai.ts)
[ ] Supabase CRUD 헬퍼 (src/lib/db.ts)
[ ] 캐릭터 상태 컴포넌트
    ─ hp/hunger/mood → 이미지 선택 로직 (11종)
    ─ GPT 대사 생성
    ─ 수치 직접 노출 금지 원칙 유지
[ ] 식사 기록 (텍스트)
    ─ 식약처 API 칼로리 조회
    ─ GPT-4o-mini fallback
    ─ meal_log 저장
[ ] 식사 기록 (사진)
    ─ GPT-4o-mini Vision 분석
[ ] 체중 기록 + 추이 그래프 (recharts, 14일)
[ ] 날씨 표시
    ─ 기상청 API 연동
    ─ 미세먼지 (에어코리아)
    ─ 날씨 → 캐릭터 이미지 자동 반영
```

---

## Phase 3 — 확장 기능

**목표:** 일정·일기·이메일 기능 웹앱 구현

```
[ ] 일정 관리
    ─ 등록·목록·삭제 (schedules 테이블)
    ─ 브라우저 Notification API 알림
    ─ 반복 일정
[ ] 일기 + 감정 분석
    ─ 작성 (textarea)
    ─ GPT-4o-mini 감정 분석
    ─ 주간 감정 추이 차트
[ ] 이메일 모니터링
    ─ n8n IMAP 폴링 → Supabase 저장
    ─ Supabase Realtime → 웹앱 실시간 반영
    ─ 발신자 관리 (화이트리스트)
```

---

## Phase 4 — n8n 연동

**목표:** ML 파이프라인 + 음식 추천 + 이메일 자동화

```
[ ] 음식 추천 웹훅 연결 (VITE_N8N_FOOD_WEBHOOK_URL)
[ ] 음식 추천 UI (잔여 칼로리 기반)
[ ] ML 의도 분류 파이프라인
    ─ GPT 라벨링 → intent_log 축적
    ─ 50건+ 누적 → ML 모델 학습 (n8n 처리)
    ─ ML 모델 → 빠른 라우팅, GPT는 엔티티 추출만
[ ] 이메일 모니터링 n8n 워크플로우 확인
```

---

## Phase 5 — 알림 · 주간 리포트

**목표:** 리포트 페이지 + Discord Webhook + 이메일 발송

```
[ ] 주간 리포트 페이지 (/report)
    ─ 주간 칼로리 차트
    ─ 체중 변화
    ─ 감정 추이
    ─ 스트릭 + 배지 7종
    ─ CSS 풀 커스텀 (Discord 임베드 한계 해소)
[ ] Discord Webhook 발송 (src/lib/discord.ts)
[ ] 이메일 발송 (n8n SMTP 워크플로우)
[ ] 브라우저 Push 알림 (PWA Service Worker)
```

---

## Phase 6 — 마무리 (선택)

```
[ ] PWA 설정
    ─ manifest.json, service worker
    ─ 모바일 홈 화면 추가 가능
[ ] Electron 패키징 (선택)
    ─ exe 데스크톱 앱
    ─ 백그라운드 실행 + 시스템 트레이
    ─ OS 네이티브 알림
```

---

## 인프라 고려사항 (20인 기준)

| 항목 | 내용 |
|------|------|
| Supabase Auth | 20인 계정 — Free tier 충분 |
| Supabase DB | RLS로 유저별 격리 — 쿼리 최적화 필요 |
| GPT API 비용 | 20인 × 일평균 호출 수 기준 월 예산 산정 필요 |
| n8n | 클라우드 n8n 또는 VPS 자체 호스팅 |
| 이미지 생성 | NovelAI — 서버사이드 처리 필요 (Edge Function 또는 n8n) |

---

## 레거시 Python 봇 처리 계획

| 시점 | 처리 |
|------|------|
| Phase 2 완료 | Python 봇 신규 개발 중단. `develop` 브랜치 보존 |
| Phase 5 완료 | `v3.2-legacy` 태그 추가 |
| 안정화 후 | Python 봇 README에 "deprecated" 표기, 아카이브 |
