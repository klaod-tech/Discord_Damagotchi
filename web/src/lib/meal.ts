import { supabase } from './supabase'
import { analyzeMealText } from './openai'

export async function recordMeal(
  userId: string,
  foodText: string,
  mealType: string = 'unknown'
) {
  const items = await analyzeMealText(foodText)
  if (!items.length) return null

  const totalCalories = items.reduce((sum, i) => sum + i.calories, 0)
  const foodName = items.map(i => i.food).join(', ')

  await supabase.from('meal_log').insert({
    user_id: userId,
    food_name: foodName,
    calories: totalCalories,
    meal_type: mealType,
  })

  // 타마고치 상태 업데이트
  const { data: tama } = await supabase
    .from('tamagotchi')
    .select('*')
    .eq('user_id', userId)
    .maybeSingle()

  if (tama) {
    const newHunger = Math.min(100, tama.hunger + 30)
    const newMood = Math.min(100, tama.mood + 10)
    const newHp = Math.min(100, tama.hp + 5)
    await supabase.from('tamagotchi').update({
      hunger: newHunger,
      mood: newMood,
      hp: newHp,
      last_fed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }).eq('user_id', userId)
  } else {
    // 타마고치 첫 생성
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
