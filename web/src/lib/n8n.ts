import axios from 'axios'

const N8N_FOOD_URL = import.meta.env.VITE_N8N_FOOD_WEBHOOK_URL

export async function requestFoodRecommendation(
  userId: string,
  address: string,
  calRemaining: number,
  mood: string = ''
) {
  const res = await axios.post(N8N_FOOD_URL, {
    user_id: userId,
    address,
    cal_remaining: calRemaining,
    mood,
  })
  return res.data
}
