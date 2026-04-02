# 게임 규칙 — 수치 변화 & 이미지 시스템

## 수치 변화 규칙

### hunger (배부름, 높을수록 배부름)
| 상황 | 변화 |
|------|------|
| 적정 식사 (400~799 kcal) | +35 |
| 과식 (800 kcal 이상) | +50 |
| 소식 (400 kcal 미만) | +15 |
| 시간 경과 | -5/시간 |
| hunger = 0 | 유지 (사망 없음, hungry_cry 이미지 유지) |

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
1순위: 특별 이벤트    goal_achieved, birthday
2순위: 식사 상태      eating, overfed, underfed
3순위: 배고픔         hungry_cry, hungry
4순위: 날씨           dusty > rainy/snowy > hot/cold > sunny/cloudy
5순위: 기본 감정      sick < tired < normal < happy
```

> **구현 위치**: `utils/image.py` → `select_image()`

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
