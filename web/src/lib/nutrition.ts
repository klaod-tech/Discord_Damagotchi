const FOOD_API_KEY = import.meta.env.VITE_FOOD_API_KEY
const FOOD_API_URL = 'https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo01/getFoodNtrCpntDbInq01'

interface NutritionResult {
  calories: number
  protein: number
  carbs: number
  fat: number
  fiber: number
  source: '식약처' | 'GPT'
}

function parseQuantity(name: string): [string, number] {
  const pattern = /(\d+(?:\.\d+)?)\s*(개|인분|그릇|접시|조각|장|캔|병|컵|잔|봉|팩|마리|줄|판)/
  const m = name.match(pattern)
  if (m) {
    const qty = parseFloat(m[1])
    const clean = name.replace(pattern, '').trim()
    return [clean, qty]
  }
  return [name, 1.0]
}

function toFloat(val: unknown): number {
  const n = parseFloat(String(val ?? 0))
  return isNaN(n) ? 0 : n
}

export async function searchFoodNutrition(foodName: string): Promise<NutritionResult | null> {
  if (!FOOD_API_KEY) return null

  const [cleanName, qty] = parseQuantity(foodName)

  const params = new URLSearchParams({
    serviceKey: FOOD_API_KEY,
    pageNo: '1',
    numOfRows: '3',
    type: 'json',
    FOOD_NM_KOR: cleanName,
  })

  try {
    const res = await fetch(`${FOOD_API_URL}?${params}`, { signal: AbortSignal.timeout(5000) })
    if (!res.ok) return null

    const data = await res.json()
    const items = data?.body?.items
    if (!items?.length) return null

    const item = items[0]
    const apiFoodName: string = item.FOOD_NM_KOR ?? ''

    // 음식명 유사성 체크
    if (!cleanName.includes(apiFoodName.slice(0, 2)) && !apiFoodName.includes(cleanName.slice(0, 2))) {
      return null
    }

    const servingG = toFloat(item.SERVING_WT) || 100
    const factor = (servingG / 100) * qty

    const calories = Math.round(toFloat(item.ENERC) * factor)
    if (calories <= 0) return null

    console.log(`[nutrition] '${cleanName}' ×${qty} 식약처 조회 성공 (${calories}kcal)`)

    return {
      calories,
      protein: Math.round(toFloat(item.PROT) * factor * 10) / 10,
      carbs:   Math.round(toFloat(item.CHO)  * factor * 10) / 10,
      fat:     Math.round(toFloat(item.FAT)  * factor * 10) / 10,
      fiber:   Math.round(toFloat(item.FIBTG)* factor * 10) / 10,
      source: '식약처',
    }
  } catch {
    return null
  }
}
