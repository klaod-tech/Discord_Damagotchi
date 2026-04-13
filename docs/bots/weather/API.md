# 날씨봇 — API 상세 가이드

---

## 1. 기상청 초단기실황 API

| 항목 | 내용 |
|------|------|
| URL | `http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst` |
| 환경변수 | `WEATHER_API_KEY` |
| 좌표 체계 | 격자 좌표 (nx, ny) — `_find_grid(city)` 참조 |
| 타임아웃 | 10초 |

### 요청 파라미터

```python
params = {
    "serviceKey": WEATHER_API_KEY,
    "numOfRows":  10,
    "pageNo":     1,
    "dataType":   "JSON",
    "base_date":  "YYYYMMDD",    # 오늘
    "base_time":  "HH00",        # 현재 시각 (정각)
    "nx":         nx,
    "ny":         ny,
}
```

### 카테고리 코드

| 코드 | 의미 |
|------|------|
| `PTY` | 강수 형태 (0=없음, 1=비, 2=비/눈, 3=눈, 5=빗방울, 6=빗방울/눈날림, 7=눈날림) |
| `SKY` | 하늘 상태 (1=맑음, 3=구름많음, 4=흐림) |
| `T1H` | 기온 (°C) |

### 날씨 문자열 변환

```python
if pty in (1, 5):    weather = "비"
elif pty in (2, 6):  weather = "비/눈"
elif pty in (3, 7):  weather = "눈"
elif sky == 4:       weather = "흐림"
elif sky == 3:       weather = "구름많음"
else:                weather = "맑음"
```

### 에러 처리

```python
try:
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json(content_type=None)
except Exception as e:
    return {"weather": "알 수 없음", "temp": 15.0}  # 기본값 반환
```

---

## 2. 에어코리아 미세먼지 API

| 항목 | 내용 |
|------|------|
| URL | `http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty` |
| 환경변수 | `AIR_API_KEY` |
| 범위 단위 | 시도 (sidoName) |
| 타임아웃 | 10초 |

### 요청 파라미터

```python
params = {
    "serviceKey": AIR_API_KEY,
    "returnType": "json",
    "numOfRows":  1,
    "pageNo":     1,
    "sidoName":   sido,   # "서울", "경기", "충남" 등
    "ver":        "1.0",
}
```

### 반환 값

| 필드 | 의미 |
|------|------|
| `pm10Value` | 미세먼지 (μg/m³) |
| `pm25Value` | 초미세먼지 (μg/m³) |

### 미세먼지 등급

```python
_pm_grade(pm10, pm25) -> str:
    pm10 > 150 or pm25 > 75  → "매우나쁨 😷"
    pm10 > 80  or pm25 > 35  → "나쁨 😷"
    pm10 > 30  or pm25 > 15  → "보통 😐"
    else                      → "좋음 😊"
```

### 에러 처리

```python
except Exception:
    return {"pm10": 0, "pm25": 0}  # 기본값 0 (좋음 등급)
```

---

## 3. 지원 도시 목록 (CITY_GRID)

50개 도시 지원 (서울, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 수원, 성남, 고양, 용인, 창원, 청주, 전주, 천안, 아산, 포항, 제주, 춘천, 강릉, 원주, 안양, 안산, 평택, 시흥, 파주, 의정부, 남양주, 화성, 김포, 광명, 군포, 하남, 구리, 오산, 이천, 양주, 경주, 김해, 거제, 여수, 순천, 목포, 익산, 군산, 구미, 안동, 진주, 강원, 충북, 충남 등)

미지원 도시 입력 시 → 서울 격자 좌표로 fallback
