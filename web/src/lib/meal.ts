import { supabase } from './supabase'
import { analyzeMealText } from './openai'
import { searchFoodNutrition } from './nutrition'

interface MealItem {
  food: string
  calories: number
  protein?: number
  carbs?: number
  fat?: number
  source: '식약처' | 'GPT'
}

async function analyzeFood(foodName: string): Promise<MealItem> {
  // 1순위: 식약처 API
  const nutrition = await searchFoodNutrition(foodName)
  if (nutrition) {
    return {
      food: foodName,
      calories: nutrition.calories,
      protein: nutrition.protein,
      carbs: nutrition.carbs,
      fat: nutrition.fat,
      source: '식약처',
    }
  }

  // 2순위: GPT fallback
  console.log(`[meal] '${foodName}' 식약처 미조회 → GPT fallback`)
  const gptItems = await analyzeMealText(foodName)
  if (gptItems.length) {
    return { food: gptItems[0].food, calories: gptItems[0].calories, source: 'GPT' }
  }

  return { food: foodName, calories: 0, source: 'GPT' }
}

export async function recordMeal(
  userId: string,
  foodText: string,
  mealType: string = 'unknown'
) {
  // GPT로 음식 목록 추출 (식약처는 개별 음식명 단위로 조회)
  const gptItems = await analyzeMealText(foodText)
  if (!gptItems.length) return null

  // 각 음식별 식약처 → GPT 순으로 칼로리 조회
  const items: MealItem[] = await Promise.all(
    gptItems.map(g => analyzeFood(g.food))
  )

  const totalCalories = items.reduce((sum, i) => sum + i.calories, 0)
  const foodName = items.map(i => i.food).join(', ')
  const sources = [...new Set(items.map(i => i.source))]
  console.log(`[meal] 기록: ${foodName} (${totalCalories}kcal) 출처: ${sources.join('+')}`)

  await supabase.from('meal_log').insert({
    user_id: userId,
    food_name: foodName,
    calories: totalCalories,
    meal_type: mealType,
  })

  // 타마고치 상태 업데이트
  const { data: tama } = await supabase
    .from('tamagotchi').select('*').eq('user_id', userId).maybeSingle()

  if (tama) {
    await supabase.from('tamagotchi').update({
      hunger: Math.min(100, tama.hunger + 30),
      mood:   Math.min(100, tama.mood + 10),
      hp:     Math.min(100, tama.hp + 5),
      last_fed_at: new Date().toISOString(),
      updated_at:  new Date().toISOString(),
    }).eq('user_id', userId)
  } else {
    await supabase.from('tamagotchi').insert({
      user_id: userId,
      hunger: 70,
      mood: 60,
      hp: 100,
      last_fed_at: new Date().toISOString(),
    })
  }

  return { foodName, totalCalories, items }
}
