import axios from 'axios'

export interface Restaurant {
  food_name: string
  location: string
  category: string
  reason: string
  rating: number | null
  link: string
}

export interface N8NResponse {
  message: string
  restaurants?: Restaurant[]
}

const CHAT_WEBHOOK = '/webhook/ad14deab-8a8b-4a6e-9348-c70980340d3f'
const FEEDBACK_WEBHOOK = '/webhook/5152b752-2221-467a-b7ff-d7cbe9945eab'

export async function sendToN8N(
  userId: string,
  message: string,
  location?: { city: string; village: string },
): Promise<N8NResponse> {
  const res = await axios.post(
    CHAT_WEBHOOK,
    { userId, message, ...location },
    { timeout: 60000 },
  )
  return {
    message: res.data?.message ?? '',
    restaurants: res.data?.restaurants?.length ? res.data.restaurants : undefined,
  }
}

export async function sendFeedback(params: {
  user_id: string
  food_name: string
  reaction: string
  location: string
  date: string
}) {
  await axios.post(FEEDBACK_WEBHOOK, params, { timeout: 5000 })
}
