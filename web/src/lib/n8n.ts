import axios from 'axios'

const N8N_CHAT_URL = import.meta.env.VITE_N8N_CHAT_WEBHOOK_URL

export async function sendToN8N(userId: string, message: string): Promise<string> {
  const res = await axios.post(N8N_CHAT_URL, { userId, message })
  // n8n meokurum2가 { message: "응답" } 형태로 반환
  const output = res.data?.output ?? res.data?.message ?? ''
  try {
    const parsed = JSON.parse(output)
    return parsed.message ?? output
  } catch {
    return output
  }
}
