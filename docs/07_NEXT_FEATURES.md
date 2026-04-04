# 다음 개발 계획 (v2.8 예정)
> last_updated: 2026-04-04 | 상태: 아이디어/설계 단계

이 문서는 팀원과 논의 중인 두 가지 작업을 기록한다.
- **A. 음식 추천 기능** — n8n 웹훅 연동 "뭐 먹고 싶어?" 버튼
- **B. 메인 Embed 버튼 UI 개편** — 버튼 통합 및 설정 하위 메뉴 구조 재편

---

## A. 음식 추천 기능 (n8n 웹훅 연동)

### 개요
유저가 "뭐 먹고 싶어?" 버튼을 클릭하면 Discord bot이 n8n 웹훅에 POST 요청을 보내고,
n8n 워크플로우가 위치 기반 + 식사 이력 기반 음식/식당을 추천해 결과를 반환한다.

```
[뭐 먹고 싶어?] 클릭
  → Discord bot → POST n8n 웹훅 URL
    payload: 위치 정보 + 오늘 먹은 음식 + 이번 주 먹은 음식 종류 + 남은 칼로리
  → n8n 워크플로우 실행 (팀원 담당)
    → 외부 음식/식당 API 조회
    → 추천 결과 생성
  → n8n → 응답 반환
  → Discord bot → 결과 Embed 표시 (Ephemeral)
```

### 구현 분담
| 영역 | 담당 | 내용 |
|------|------|------|
| Discord bot 쪽 | 이 repo | 버튼 핸들러, n8n POST 호출, 응답 파싱 후 embed 표시 |
| n8n 워크플로우 | 팀원 | 웹훅 수신, 외부 API 연동, 추천 로직, 응답 반환 |

---

### 웹훅 페이로드 (Discord bot → n8n)

Discord bot이 n8n에 POST로 보낼 데이터.

```json
{
  "user_id": "123456789",
  "location": {
    "city": "서울",
    "address": "마포구 합정동"
  },
  "remaining_calories": 620,
  "today_calories": 1380,
  "daily_cal_target": 2000,
  "today_meals": [
    "비빔밥",
    "아메리카노"
  ],
  "weekly_meals": [
    "비빔밥", "삼겹살", "라면", "치킨", "된장찌개", "카레"
  ]
}
```

**각 필드 출처:**

| 필드 | 출처 | 설명 |
|------|------|------|
| `user_id` | 상수 | Discord 유저 ID |
| `location.city` | `users.city` | 날씨용 기존 도시명 |
| `location.address` | `users.address` (신규) | 구/동 단위 상세 주소 ⚠️ 미결 |
| `remaining_calories` | `daily_cal_target - today_calories` | 오늘 남은 칼로리 |
| `today_calories` | `get_today_calories(user_id)` | 오늘 총 섭취 칼로리 |
| `daily_cal_target` | `users.daily_cal_target` | 일일 목표 칼로리 |
| `today_meals` | `get_today_meals(user_id)` | 오늘 food_name 목록 |
| `weekly_meals` | `get_weekly_meal_stats(user_id, 7일 전)` | 이번 주 food_name 목록 (중복 제거) |

---

### n8n 응답 포맷 ⚠️ 미정

응답 포맷은 팀원이 n8n 워크플로우 구성 후 확정한다.
확정되면 아래 항목을 채워야 한다.

```
[ ] 응답 Content-Type: application/json 여부
[ ] 추천 결과 JSON 구조 예시
    예시 후보:
    {
      "recommendations": [
        {
          "name": "맛있는 냉면",
          "category": "한식",
          "address": "서울 마포구 ...",
          "distance": "도보 5분",
          "calories_estimate": "약 500~700 kcal"
        }
      ],
      "message": "오늘 저녁엔 가볍게 냉면 어때?"
    }
[ ] 추천 개수 (1개? 3개?)
[ ] 칼로리 정보 포함 여부
[ ] 실패 시 에러 응답 형식
```

> **Discord bot 쪽 구현 시작 조건:** 응답 포맷 확정 후 파싱/embed 코드 작성.
> 포맷 확정 전에는 버튼 + 웹훅 POST 전송 부분만 먼저 구현 가능.

---

### 환경변수 추가 필요

```
N8N_FOOD_WEBHOOK_URL   # n8n 음식 추천 웹훅 URL
                       # 예: https://your-n8n.app/webhook/food-recommend
```

`.env`와 플랫폼 시크릿에 추가 필요.

---

### 위치 정보 상세화 (⚠️ 미결 — 결정 필요)

현재 `users.city` 필드는 "서울", "부산" 등 시 단위만 저장한다.  
음식 추천의 정확도를 높이려면 "마포구", "합정동" 수준의 상세 주소가 필요하다.

#### 문제: 기존 city 필드와 날씨 API의 관계

```python
# cogs/weather.py — 현재 city → 기상청 격자 좌표 매핑
CITY_GRID = {
    "서울": (60, 127),
    "마포구": ???  # 매핑 없음
}
```

`city` 필드를 "서울 마포구"로 바꾸면 기상청 격자 좌표 매핑이 깨진다.

#### 옵션 A: `city` 필드 확장 + 날씨 API 매핑 로직 수정

```
city = "서울 마포구 합정동"

날씨 API 매핑 로직:
  앞 단어(시/도)만 파싱 → "서울" → CITY_GRID["서울"]

음식 추천 페이로드:
  address = city 전체 그대로 전달
```

- 장점: 필드 1개로 통합 관리
- 단점: `weather.py` `_find_grid()` 수정 필요, 기존 유저 데이터 마이그레이션 필요

#### 옵션 B: `address` 필드 별도 추가 (권장)

```
city    = "서울"        → 날씨 API 전용 (기존 그대로)
address = "마포구 합정동" → 음식 추천 전용 (신규)
```

- 장점: 날씨 API 코드 무변경, 기존 유저 데이터 영향 없음
- 단점: 온보딩 Modal 필드 1개 추가 (4→5개, Discord Modal 최대 5개라 정확히 한계)

```python
# 온보딩 Modal 변경 시 (옵션 B)
class OnboardingModal(discord.ui.Modal, title="먹구름 시작하기"):
    tama_name   = ...  # 기존
    city        = ...  # 기존 (시 단위 유지)
    address     = discord.ui.TextInput(  # 신규
        label="상세 위치 (구/동)",
        placeholder="예: 마포구 합정동, 강남구 역삼동",
        max_length=30,
    )
    weight_info = ...  # 기존
    body_info   = ...  # 기존
```

> **결정 전 체크리스트:**
> - [ ] 기존 유저(city만 있는 경우) address NULL 처리 방식
> - [ ] 설정 변경에서 address 수정 가능하게 할지
> - [ ] n8n 워크플로우가 city만으로도 동작 가능한지 (address 없을 때 fallback)

---

## B. 메인 Embed 버튼 UI 개편

### 현재 버튼 구조 (v2.7)

```
Row 0: [🍽️ 식사 입력] [📊 오늘 요약] [📅 오늘 일정]
Row 1: [⚙️ 설정 변경] [⏰ 시간 설정] [⚖️ 체중 기록]
```

**문제점:**
- "오늘 요약"과 "오늘 일정" 기능 범위가 겹침 (둘 다 오늘 칼로리/GPT 코멘트 포함)
- "시간 설정"이 최상위에 노출될 필요 없음 — 자주 쓰는 기능이 아님
- "뭐 먹고 싶어?" 버튼 추가 공간 필요

### 변경 후 버튼 구조 (v2.8 목표)

```
Row 0: [🍽️ 식사 입력] [📋 하루 정리] [🍜 뭐 먹고 싶어?]
Row 1: [⚙️ 설정]      [⚖️ 체중 기록]
```

총 5개로 정리. 설정 버튼 클릭 시 하위 메뉴 에페메럴로 표시.

---

### "하루 정리" 통합 내용

기존 "오늘 요약" + "오늘 일정"을 하나로 통합.

```
📋 하루 정리 — {날짜}

🔥 칼로리 현황           (기존 요약 + 일정 통합)
  목표: 2000 kcal  현재: 1380 kcal  (69%)
  `███████░░░`

🥗 탄단지 비율           (기존 요약)
  탄수화물 180g | 단백질 65g | 지방 42g

🍽️ 오늘 끼니             (기존 요약)
  🌅 아침: 토스트 — 350 kcal
  ☀️ 점심: 비빔밥 — 580 kcal
  ...

⚖️ 체중 현황             (기존 일정)
  현재: 71.8kg (▼ 0.5kg)
  목표까지: 1.8kg 남음

🌤️ 오늘 날씨             (기존 일정)
  맑음 / 18°C  📍 서울
  미세먼지: 좋음

🍽️ 식사 알림             (기존 일정)
  🌅 08:00  ☀️ 12:00  🌙 18:00

🐣 {타마} 한마디          (GPT 1회 호출로 통합)
  *"..."*
```

**구현 시 변경 파일:**
- `utils/embed.py` — `MainView` 버튼 재편, `today_button` + `summary_button` → `daily_summary_button` 통합
- `cogs/summary.py` — `send_summary()` 로직을 새 통합 핸들러로 이전
- `utils/embed.py` `today_button` 로직 → 같은 핸들러로 통합

> **⚠️ 주의**: `custom_id` 변경 시 (`btn_summary`, `btn_today` → 새 ID)
> 기존 Discord 메시지에 붙어있는 버튼이 동작 안 할 수 있음.
> 봇 재시작 + `!소환` 커맨드로 embed 재생성 필요.

---

### "설정" 하위 메뉴 구조

"설정 변경" 버튼 클릭 시 에페메럴 메시지에 하위 버튼 표시.

```
[⚙️ 설정] 클릭
  → Ephemeral: "어떤 설정을 변경할까?"
    [👤 내 정보]   [📍 위치 설정]   [⏰ 시간 설정]
```

| 하위 버튼 | 기존 | 변경 후 |
|---------|------|---------|
| [👤 내 정보] | SettingsModal (이름+도시+목표체중) | 이름 + 목표체중만 |
| [📍 위치 설정] | 없음 (신규) | 날씨용 도시 + 음식추천용 상세 주소 |
| [⏰ 시간 설정] | 최상위 버튼 | 설정 하위로 이동 |

**구현 시 변경 파일:**
- `utils/embed.py` — `MainView`에서 시간 설정 버튼 제거, 설정 버튼 클릭 핸들러 수정
- `cogs/settings.py` — `SettingsModal` 분리 (내 정보 / 위치 설정), `SettingsSubView` 신규 추가

---

## 전체 구현 순서 (권장)

```
Phase 1 — UI 개편 (코드 변경, n8n 불필요)
  [ ] "하루 정리" 통합 (summary + today 합치기)
  [ ] 설정 하위 메뉴 구조 (SettingsSubView)
  [ ] MainView 버튼 5개로 재편

Phase 2 — 위치 정보 결정 및 DB 반영
  [ ] 옵션 A vs B 결정
  [ ] 결정에 따라 온보딩 Modal, DB 컬럼, 설정 변경 Modal 수정

Phase 3 — n8n 연동 (n8n 응답 포맷 확정 후)
  [ ] N8N_FOOD_WEBHOOK_URL 환경변수 추가
  [ ] 버튼 핸들러 + aiohttp POST 호출 구현
  [ ] n8n 응답 파싱 + Embed 표시
  [ ] 오류 처리 (타임아웃, n8n 응답 실패 등)
```

---

## 미결 사항 체크리스트

```
[ ] 위치 필드: 옵션 A (city 확장) vs 옵션 B (address 별도 추가) 결정
[ ] n8n 응답 포맷 확정 (팀원)
[ ] "하루 정리" 통합 시 섹션 순서/표시 방식 최종 확인
[ ] 음식 추천 버튼 이름 확정 ("🍜 뭐 먹고 싶어?" 가칭)
[ ] n8n 웹훅 URL 전달 (팀원 → 환경변수 등록)
[ ] 기존 유저 address NULL 처리 방식 (옵션 B 선택 시)
```
