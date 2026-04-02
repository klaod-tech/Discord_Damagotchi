# 프로젝트 개요

## 한 줄 소개
먹구름(mukgoorm) — 유저가 음식을 입력하면 나만의 캐릭터에게 밥을 주는 행위로 연결되며, 칼로리/날씨 정보를 **수치 없이 캐릭터 이미지와 대사로 간접 전달**하는 디스코드 식습관 관리 봇.

---

## 핵심 원칙 (절대 변경 불가)
1. **hp/hunger/mood 수치는 사용자에게 절대 직접 노출 금지** — 이미지+대사로만 간접 표현
2. **날씨는 별도 알림 없음** — 기상 시간에 이미지 자동 교체로만 전달
3. **칼로리/영양소 수치는 오늘 요약 버튼 클릭 시 Ephemeral로만 확인 가능**
4. **파일명 소문자 고정** (eat.png O, Eat.PNG X)

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| 언어 | Python 3.11+ |
| 디스코드 | discord.py 2.x |
| AI | OpenAI GPT-4o (칼로리 분석, Vision, 대사 생성) |
| 날씨 | 기상청 공공데이터 API (초단기실황조회) |
| 미세먼지 | 에어코리아 API (PM10, PM2.5) |
| DB | Supabase (PostgreSQL) — psycopg2, Session pooler |
| 스케줄러 | APScheduler (AsyncIOScheduler) |
| ML | scikit-learn (Ridge / RandomForest), pandas, numpy |
| 칼로리 공식 | Mifflin-St Jeor |
| 이미지 | NovelAI (NAI Diffusion Anime V3, 512×512) |

---

## 환경변수 (.env)

```
DISCORD_TOKEN          # 디스코드 봇 토큰
OPENAI_API_KEY         # OpenAI API 키
WEATHER_API_KEY        # 기상청 공공데이터 포털 인증키
AIR_API_KEY            # 에어코리아 API 키
DATABASE_URL           # Supabase Session pooler URL
                       # 형식: postgresql://postgres.{project_id}:{password}@...
TAMAGOTCHI_CHANNEL_ID  # #다마고치 채널 ID
```

---

## 디스코드 채널 구조

```
#다마고치 채널 (일반 채팅 불가, 봇만 허용)
├── [고정 메시지] 시작하기 Embed → 버튼: [🐣 다마고치 시작하기]
└── 쓰레드 목록 (유저별 전용)
    ├── {tamagotchi_name}의 다마고치 → 유저A 전용
    └── ...
```

---

## 버전 히스토리

| 버전 | 날짜 | 주요 변경사항 |
|------|------|--------------|
| v1.0 | 2026-03-25 | 전체 설계, DB 구조, 기술스택 확정, GitHub 생성 |
| v1.1 | 2026-03-28 | 온보딩 Modal, 쓰레드 생성, 메인 Embed UI |
| v1.2 | 2026-03-28 | SQLite → Supabase(PostgreSQL) 전환 |
| v1.3 | 2026-03-28 | 식사 입력 Modal, GPT 자연어 파싱, 소급입력 |
| v1.4 | 2026-03-28 | 오늘요약/오늘일정/설정변경 버튼 (4개 확정) |
| v1.5 | 2026-03-28 | 기상청+에어코리아 API, 날씨 Embed 이미지 교체 |
| v1.6 | 2026-03-29 | 오후 10시 칼로리 판정 스케줄러 |
| v1.7 | 2026-03-31 | ML(pattern/ml/bridge), Vision 사진입력, 체중기록 |
| v1.8 | 2026-04-02 | 이미지 파일명 정리 (11종 확정), 문서 구조화 |
| v1.9 | 2026-04-02 | 시간 설정 Select Menu 분리 (cogs/time_settings.py), 메인 Embed 버튼 6개 2행 재편 |
| v2.0 | 2026-04-02 | P2 수정: gender/age/height DB 저장, settings.py 하드코딩 제거, psycopg2-binary requirements 추가, weight_log init_db 등록 |
| v2.1 | 2026-04-02 | 프로젝트명 먹구름(mukgoorm) 확정, GPT 캐릭터 프롬프트 수정 (다마고치 정체성 → 범용 캐릭터), utils/cogs/ 데드코드 삭제 |
| v2.2 | 2026-04-02 | 식사 알림 스케줄러 구현 (3단계 Job + hourly hunger decay), bot.py on_ready 시 전체 유저 Job 등록 |
| v2.3 | 2026-04-03 | DB 타임존 버그 수정 (UTC→KST 이중변환), 메인 Embed 이미지 크게 표시 (set_thumbnail 제거), 칼로리 0 식사 저장 차단, 커맨드 로깅 추가 |
| v2.4 | 2026-04-03 | 오늘 요약 footer 제거, 시간 설정 분 단위 10분으로 변경, 시간 설정 UI 레이블 개선 |

---

## GitHub
- Repo: https://github.com/klaod-tech/Discord_Damagotchi
- 메인 브랜치: `main`
- 개발 브랜치: `develop` ← **모든 개발은 여기서**
