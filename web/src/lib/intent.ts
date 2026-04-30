import OpenAI from 'openai'

const client = new OpenAI({
  apiKey: import.meta.env.VITE_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true,
})

export type Intent = 'meal' | 'weight' | 'diary' | 'schedule' | 'weather' | 'email' | 'report' | 'none'

export interface IntentResult {
  intent: Intent
  reply: string
  entities: Record<string, string>
}

export async function analyzeIntent(message: string, userName: string): Promise<IntentResult> {
  const res = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      {
        role: 'system',
        content: `너는 ${userName}의 귀여운 AI 캐릭터 먹구름이야.
유저 메시지를 분석해서 의도를 파악하고 JSON으로만 응답해.

의도 종류:
- meal: 식사 기록 (음식 먹었다, 식사 입력 등)
- weight: 체중 기록 (몸무게, kg 등)
- diary: 일기/감정 (오늘 하루, 기분 등)
- schedule: 일정 (약속, 예약, 알림 등)
- weather: 날씨 확인
- email: 이메일 확인
- report: 주간 리포트
- none: 일반 대화

응답 형식 (JSON만):
{
  "intent": "meal",
  "reply": "오늘 점심 뭐 먹었어? 맛있었겠다!",
  "entities": {"food": "비빔밥", "meal_type": "점심"}
}

reply는 캐릭터 말투로 짧게 (30자 이내), 수치 절대 언급 금지.`,
      },
      { role: 'user', content: message },
    ],
    max_tokens: 200,
    response_format: { type: 'json_object' },
  })

  try {
    return JSON.parse(res.choices[0].message.content ?? '{}')
  } catch {
    return { intent: 'none', reply: '응? 잘 못 들었어 😅', entities: {} }
  }
}
