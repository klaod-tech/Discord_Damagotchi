# 다음 작업 목록

> 최종 업데이트: 2026-05-26  
> 브랜치: `feat/web-migration`

---

## ✅ 완료된 작업

### n8n (먹구름_봇v4)
| 항목 | 상태 |
|---|---|
| 날씨 webhook | ✅ |
| 식사 webhook | ✅ |
| 일기 webhook | ✅ |
| 일정 webhook | ✅ |
| 체중 webhook | ✅ |
| 음식추천 A/B/C 경로 (Softmax 정렬) | ✅ |
| B/C 경로 응답에 menus 포함 (Step 3-1) | ✅ |
| Step 3-3: /food/select 흐름 구조 | ✅ v4에 존재 |
| Step 4: /worldcup 흐름 구조 | ✅ v4에 존재 |

### React
| 항목 | 상태 |
|---|---|
| 피드백 버튼 UI (선택 시 glow 효과, 중복 클릭 방지) | ✅ |
| `sendFeedback` → POST body에서 `reaction` 키로 변환 | ✅ |
| `Restaurant` interface에 `menus?: MenuItem[]` 추가 (Step 3-2) | ✅ |
| `fetchRestaurantMenu` 제거 → `restaurant.menus` 직접 사용 (Step 3-2) | ✅ |
| `allergens` 제거 → `keywords` 블루 태그로 교체 (`Home.tsx`) | ✅ |
| `Onboarding.tsx` — 알레르기 UI 전체 제거 | ✅ |
| `Settings.tsx` — 알레르기 UI 전체 제거 | ✅ |
| `Worldcup.tsx` — 완성 (FOOD_POOL 16개, top_categories 렌더링) | ✅ |
| 이메일 카드 표시 — 5개 전체, 신규/기존 배지, 펼치기 요약 (`Home.tsx`) | ✅ |
| `EmailItem` 인터페이스 + `CombinedResponse.emails` 추가 (`n8n.ts`) | ✅ |
| `BOT_TIMEOUT` — 이메일 60초 타임아웃 (`n8n.ts`) | ✅ |
| 음식추천 타임아웃 180초로 증가 — `recommendFood()` (`n8n.ts`) | ✅ |
| `CLASSIFY_PROMPT` 날씨 규칙 강화 — 직접 질문 시에만 날씨 봇 호출 (`n8n.ts`) | ✅ |
| 로그아웃 버튼 추가 — 계정 관리 섹션, 회원탈퇴 옆 (`Settings.tsx`) | ✅ |

### Supabase
| 항목 | 상태 |
|---|---|
| `food_feedback` 테이블에 `restaurant_id` 컬럼 추가 | ✅ |
| `user_preference_logits` 온보딩 시 0으로 초기화 | ✅ |
| `menu_items.allergens` — 사용 중단 (dead column 유지) | ✅ |
| `menu_items.keywords text[]` 컬럼 추가 | ✅ |
| 전체 메뉴 약 703개 키워드 입력 완료 | ✅ |

---

## n8n 버그 현황 (`음식 추천 v2 (13).json`)

n8n 캔버스에서 직접 수정 후 Save → Active 확인.

---

### ✅ [완료] 피드백 로직 — `피드백 현재 로직` 테이블 오류

`피드백 현재 로직` 노드 테이블을 `user_preference_logits`으로 수정 완료.

상세: [guide/n8n_02_피드백_로짓.md](guide/n8n_02_피드백_로짓.md)

---

### ✅ [완료] 메뉴 선택 — `메뉴 선택 로직 계산` exists 누락

`메뉴 선택 로직 계산` Code 노드 return에 `exists: !!existing` / `exists: !!existingSkip` 추가 완료.

상세: [guide/n8n_03_메뉴선택_로짓.md](guide/n8n_03_메뉴선택_로짓.md)

---

### 월드컵 — `Code in JavaScript` 노드 참조 + 응답 형식

**✅ 버그 1 — 노드 참조 오류:** `$('월드컵 로직 계산')` 수정 완료.

**✅ 버그 2 — 응답 형식 오류:** `피드백 확인1` 노드 Response Body `top_categories` 누락 수정 완료.

상세: [guide/n8n_04_worldcup.md](guide/n8n_04_worldcup.md)
