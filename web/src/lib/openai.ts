import OpenAI from 'openai'

const client = new OpenAI({
  apiKey: import.meta.env.VITE_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true,
})

export async function generateComment(prompt: string): Promise<string> {
  const res = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: prompt }],
    max_tokens: 200,
  })
  return res.choices[0].message.content ?? ''
}

export async function analyzeMealText(text: string): Promise<{ food: string; calories: number }[]> {
  const res = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      {
        role: 'system',
        content: '음식명과 칼로리를 JSON 배열로만 응답해. 형식: [{"food":"음식명","calories":숫자}]',
      },
      { role: 'user', content: text },
    ],
    max_tokens: 300,
  })
  try {
    return JSON.parse(res.choices[0].message.content ?? '[]')
  } catch {
    return []
  }
}

export async function analyzeMealPhoto(base64Image: string): Promise<{ food: string; calories: number }[]> {
  const res = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'image_url',
            image_url: { url: `data:image/jpeg;base64,${base64Image}` },
          },
          {
            type: 'text',
            text: '이 음식 사진의 음식명과 예상 칼로리를 JSON 배열로만 응답해. 형식: [{"food":"음식명","calories":숫자}]',
          },
        ],
      },
    ],
    max_tokens: 300,
  })
  try {
    return JSON.parse(res.choices[0].message.content ?? '[]')
  } catch {
    return []
  }
}
