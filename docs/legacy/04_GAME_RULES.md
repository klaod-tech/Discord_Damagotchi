# 게임 규칙 — 수치 변화 & 이미지 시스템

## 수치 변화 규칙

### hunger (배부름, 높을수록 배부름)
| 상황 | 변화 |
|------|------|
| 적정 식사 (400~799 kcal) | +35 |
| 과식 (800 kcal 이상) | +50 |
| 소식 (400 kcal 미만) | +15 |
| 시간 경과 | -5/시간 |
| hunger = 0 | 유지 (사망 없음, upset.png 이미지 유지) |

> **구현 위치**: `utils/embed.py` → `_hunger_gain(calories)`

### hp (건강)
| 상황 | 변화 |
|------|------|
| 식사 입력 | +5 |
| 과식 3일 연속 | -10 |
| 소식 3일 연속 | -10 |

### mood (기분)
| 상황 | 변화 |
|------|------|
| 식사 입력 | +5 |
| 오늘 요약 버튼 클릭 | +3 |
| hunger < 30 | -10 |

### 이벤트 효과 코드 참조
```python
EVENT_EFFECTS = {
    "meal_input": {"hunger": +35, "mood": +5, "hp": +5},
    "overmeal":   {"hunger": +50},
    "undermeal":  {"hunger": +15},
}
```

---

## 이미지 선택 우선순위

```
1순위: 특별 이벤트    cheer.png (목표 달성)
2순위: 식사 직후      eat.png (last_fed_at 기준 3분 이내)
3순위: 배고픔         upset.png (hunger < 40)
4순위: 날씨           wear mask > rainy/snow > hot/warm > (맑음/흐림 → 없음)
5순위: 기본 감정      tired < normal < smile
```

> **구현 위치**: `utils/image.py` → `select_image()`

---

## 스트릭 & 도전과제 배지 (v2.7)

### 스트릭 (연속 기록)
| 상황 | 변화 |
|------|------|
| 오늘 식사 기록 1건 이상 | streak + 1 |
| 오늘 식사 기록 없음 | streak = 0 초기화 |

- `streak ≥ 3` 상태에서 끊기면 아쉬운 메시지 전송
- `max_streak`: 역대 최고 연속 기록일 별도 보관

> **구현 위치**: `cogs/scheduler.py` → `_nightly_analysis()` (매일 22:00)

### 도전과제 배지
| 배지 ID | 이름 | 달성 조건 |
|---------|------|----------|
| `first_meal` | 🍽️ 첫 끼니 | 첫 번째 식사 기록 |
| `streak_3` | 🔥 3일 연속 | streak ≥ 3 |
| `streak_7` | 🌟 일주일 달인 | streak ≥ 7 |
| `streak_30` | 👑 한 달 챔피언 | streak ≥ 30 |
| `calorie_10` | 🎯 목표 달성 10회 | 하루 총 칼로리 ≥ 목표 90% 달성일 10일 이상 |
| `photo_10` | 📸 사진 마스터 | 사진 입력 누적 10회 이상 |
| `morning_7` | 🌅 아침형 인간 | 아침 끼니 누적 기록 7회 이상 |

- 배지 달성 시: 골드 색상 Embed 전송 + 메인 Embed `cheer.png` 갱신
- 배지 정보는 `users.badges` (JSON 배열)에 저장
- 중복 수여 없음 (한 번 획득하면 영구 보유)

> **구현 위치**: `utils/badges.py` → `check_new_badges()`, `cogs/scheduler.py` → `_nightly_analysis()`

---

## 이미지 트리거 조건 (압축 버전)

| 파일명 | 트리거 조건 | 우선순위 |
|--------|------------|---------|
| `cheer.png` | 목표 체중 달성 | 1 |
| `eat.png` | 식사 입력 직후 3분 이내 | 2 |
| `upset.png` | hunger < 40 (배고픔 통합) | 3 |
| `wear mask.png` | PM10 > 80 OR PM2.5 > 35 | 4 |
| `rainy.png` | 날씨 = 비/소나기 | 4 |
| `snow.png` | 날씨 = 눈 | 4 |
| `hot.png` | 기온 ≥ 26°C | 4 |
| `warm.png` | 기온 ≤ 5°C (따뜻하게 입은 모습) | 4 |
| `tired.png` | hp < 40 OR mood < 40 (sick+tired 통합) | 5 |
| `smile.png` | hp ≥ 70, hunger ≥ 70, mood ≥ 70 | 5 |
| `normal.png` | 기본값 (맑음/흐림 포함) | 5 |

> **sunny(맑음 15~25°C), cloudy(흐림)** → 전용 이미지 없음, 5순위 감정 상태로 자연스럽게 넘어감  
> **overfed/underfed** → 전용 이미지 없음, 동일하게 감정 상태로 넘어감
