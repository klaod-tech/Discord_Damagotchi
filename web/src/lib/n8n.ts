import OpenAI from 'openai'
import axios from 'axios'

const client = new OpenAI({
  apiKey: import.meta.env.VITE_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true,
})

export interface Restaurant {
  restaurant_id: string
  food_name: string
  location: string
  category: string
  description: string
  phone: string
  reason: string
  link: string
  menus?: MenuItem[]
}

export interface WeatherData {
  city?: string
  temperature?: number
  low_temperature?: number
  high_temperature?: number
  sky?: string
  rain?: string
  humidity?: number
  windSpeed?: number
  pm10?: number
  pm25?: number
  pm10_grade?: string
  pm25_grade?: string
  condition?: string
  dust_level?: string
  message?: string
}

export interface ClassifyResult {
  bots: string[]
  date: string
  is_future: boolean
  location: string
  message_past: string
  message_future: string
  message: string
}

export interface EmailItem {
  sender: string
  subject: string
  summary: string
  is_new?: boolean
}

export interface CombinedResponse {
  messages: string[]
  restaurants: Restaurant[]
  weather: WeatherData[]
  emails: EmailItem[]
  failed: string[]
  food_path?: IntentPath
  food_description?: string
}

const BOT_WEBHOOK: Record<string, string> = {
  날씨: '/webhook/weather',
  일기: '/webhook/diary',
  일정: '/webhook/schedule',
  식사: '/webhook/meal',
  체중: '/webhook/weight',
  이메일: '/webhook/email',
  // 음식추천은 recommendFood()로 별도 호출 — 여기 넣지 말 것
}

const DEFAULT_TIMEOUT = 30000
const BOT_TIMEOUT: Record<string, number> = {
  이메일: 300000,
}

const FEEDBACK_WEBHOOK = '/webhook/feedback'

const CLASSIFY_PROMPT = `당신은 사용자 채팅을 분석하는 AI입니다.
오늘 날짜: {TODAY}

반드시 순수 JSON만 출력하세요. 다른 텍스트 금지. 마크다운 코드블록(\`\`\`) 절대 사용 금지.
해당되는 봇이 여러 개면 반드시 모두 bots 배열에 포함하세요.

[봇 선택 규칙]
- 날씨: 날씨/기온/미세먼지/습도/비/눈을 직접 묻는 경우만 (과거 경험 언급·일기 맥락에서 날씨 언급은 제외)
- 식사: 음식 섭취, 식사, 음료를 먹었다는 과거 기록
- 일기: 오늘/과거에 실제로 경험한 일, 감정, 장소 방문 (어제, 그제, N일전, 아까 등 포함)
- 일정: 미래의 약속, 계획, 구체적 행동 예정
- 체중: 실제 체중/몸무게 숫자를 측정·기록하는 경우만 (예: "74kg 찍었어", "몸무게 재니 76이야")
  ❌ 제외: 체중 걱정만 언급, 헬스장/운동/다이어트 일반 언급, 운동을 했다는 일기 기록
- 이메일: 메일 확인 요청
- 음식추천: 음식/맛집 추천, 근처 식당 검색

[복합 메시지]
여러 의도가 섞이면 해당하는 봇 모두 선택

[날짜 변환]
날짜 언급 시 "yyyy-MM-dd"로 변환. 없으면 오늘 날짜.
- 어제 → 오늘 -1일
- 그제/그저께 → 오늘 -2일
- N일전 → 오늘 -N일 (예: "2일전" → -2일, "3일전" → -3일)
- N일 후/뒤 → 오늘 +N일

[출력 형식]
{
  "bots": ["봇이름"],
  "date": "yyyy-MM-dd",
  "is_future": true/false,
  "location": "장소 또는 빈 문자열",
  "message_past": "과거 내용 요약",
  "message_future": "미래 내용 요약",
  "message": "전체 한 줄 요약"
}`

export async function classifyMessage(message: string): Promise<ClassifyResult> {
  const today = new Date().toISOString().slice(0, 10)
  const res = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      { role: 'system', content: CLASSIFY_PROMPT.replace('{TODAY}', today) },
      { role: 'user', content: message },
    ],
    max_tokens: 400,
    response_format: { type: 'json_object' },
  })
  const parsed = JSON.parse(res.choices[0].message.content ?? '{}')
  return {
    bots: Array.isArray(parsed.bots) ? parsed.bots : [],
    date: parsed.date ?? today,
    is_future: parsed.is_future ?? false,
    location: parsed.location ?? '',
    message_past: parsed.message_past ?? '',
    message_future: parsed.message_future ?? '',
    message: parsed.message ?? '',
  }
}

export async function dispatchToWebhooks(
  userId: string,
  originalMessage: string,
  classified: ClassifyResult,
  extra?: Record<string, unknown>,
): Promise<CombinedResponse> {
  const payload = {
    user_id: userId,
    message: originalMessage,
    date: classified.date,
    is_future: classified.is_future,
    location: classified.location,
    message_past: classified.message_past,
    message_future: classified.message_future,
    is_update: false,
    ...extra,
  }

  const botEntries = classified.bots
    .map(bot => ({ bot, url: BOT_WEBHOOK[bot] }))
    .filter(e => e.url)

  const combined: CombinedResponse = { messages: [], restaurants: [], weather: [], emails: [], failed: [] }
  if (botEntries.length === 0) return combined

  const results = await Promise.allSettled(
    botEntries.map(({ bot, url }) =>
      axios
        .post<{
          message?: string
          recommendations?: Restaurant[]
          weather?: WeatherData
        }>(url, payload, { timeout: BOT_TIMEOUT[bot] ?? DEFAULT_TIMEOUT })
        .then(r => r.data),
    ),
  )

  results.forEach((result, i) => {
    if (result.status === 'fulfilled') {
      const data = result.value as Record<string, unknown>
      if (data.message) combined.messages.push(data.message as string)

      const recs = (data.restaurants ?? data.recommendations ?? []) as Restaurant[]
      if (recs.length) combined.restaurants.push(...recs)

      if (data.weather) combined.weather.push(data.weather as WeatherData)

      if (Array.isArray(data.emails)) combined.emails.push(...(data.emails as EmailItem[]))

      if (data.path) combined.food_path = data.path as IntentPath
      if (data.description) combined.food_description = data.description as string
    } else {
      combined.failed.push(botEntries[i].bot)
    }
  })
  return combined
}

export async function synthesizeResponse(
  characterName: string,
  userMessage: string,
  classified: ClassifyResult,
  combined: CombinedResponse,
): Promise<string> {
  const botResponses = combined.messages.length > 0
    ? combined.messages.join('\n')
    : '없음'

  const hasCards = combined.restaurants.length > 0 || combined.weather.length > 0

  const res = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [
      {
        role: 'system',
        content: `너는 ${characterName}이야. 귀엽고 친근한 AI 먹구름 캐릭터야.
유저 메시지에 자연스럽게 한 문단으로 답해줘.

규칙:
- ~야/~어/~해 말투, 50자 이내로 짧게
- 봇 응답이 있으면 그 내용을 자연스럽게 포함해서 답해
- 봇 응답이 없으면 유저 메시지에 공감하며 반응해
${hasCards ? '- 맛집/날씨 정보는 카드로 따로 보여줄 거니까 "찾아봤어!" 정도로만 가볍게 언급해' : ''}`,
      },
      {
        role: 'user',
        content: `유저 메시지: ${userMessage}
처리된 카테고리: ${classified.bots.join(', ') || '없음'}
봇 응답: ${botResponses}`,
      },
    ],
    max_tokens: 150,
  })

  return res.choices[0].message.content?.trim() ?? '응? 다시 말해줘 😅'
}

export async function callBotWebhook(
  endpoint: string,
  userId: string,
  message: string,
  classified: ClassifyResult,
  extra?: Record<string, unknown>,
): Promise<{ message?: string }> {
  const payload = {
    user_id: userId,
    message,
    date: classified.date,
    is_future: classified.is_future,
    location: classified.location,
    message_past: classified.message_past,
    message_future: classified.message_future,
    is_update: false,
    ...extra,
  }
  const res = await axios.post<{ message?: string }>(endpoint, payload, { timeout: 15000 })
  return res.data
}

export async function sendFeedback(params: {
  user_id: string
  restaurant_id: string
  food_name: string
  category: string
  feedback: 'like' | 'dislike'
}) {
  const { feedback, ...rest } = params
  await axios.post(FEEDBACK_WEBHOOK, { ...rest, reaction: feedback }, { timeout: 5000 })
}

// ── 음식 추천 v2: 3단계 분리 API ──────────────────────────────

export type IntentPath = 'A' | 'B' | 'C'

export interface FoodRecommendResponse {
  path: IntentPath
  description: string
  message: string
  restaurants: Restaurant[]
  keyword: string
}

export interface MenuItem {
  id: string
  menu_name: string
  price: number | null
  description: string | null
  tags: string[] | null
  keywords: string[] | null
}

export interface MenuResponse {
  restaurant_id: string
  menus: MenuItem[]
}

/** 1단계: 음식 추천 (의도 분류 → A/B/C 경로) */
export async function recommendFood(params: {
  user_id: string
  message: string
  location?: string
  date?: string
}): Promise<FoodRecommendResponse> {
  const res = await axios.post<FoodRecommendResponse>(
    '/webhook/food',
    params,
    { timeout: 180000 },
  )
  return res.data
}

/** 2단계: 메뉴 선택 기록 */
export async function selectFood(params: {
  user_id: string
  restaurant_id: string
  menu_name: string
  keywords: string[] // 로짓 업데이트 — n8n에서 keywords→category 매핑 처리
  location?: string
  date?: string
}): Promise<void> {
  await axios.post('/webhook/food/select', params, { timeout: 5000 })
}

// ── 월드컵 ────────────────────────────────────────────────────

export interface WorldcupRound {
  round: number
  winner: string
  loser: string
  winner_category: string
  loser_category: string
}

export interface WorldcupResponse {
  message: string
  top_categories: string[]
}

/** 월드컵 결과 전송 — n8n이 logit 계산·저장·worldcup_sessions 기록 모두 처리 */
export async function sendWorldcupResult(params: {
  user_id: string
  champion: string
  rounds: WorldcupRound[]
}): Promise<WorldcupResponse> {
  const res = await axios.post<WorldcupResponse>(
    '/webhook/worldcup',
    params,
    { timeout: 30000 },
  )
  return res.data
}

