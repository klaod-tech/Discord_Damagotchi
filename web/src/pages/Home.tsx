import { useEffect, useRef, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { selectCharacterImage } from '../lib/image'
import { getCharacterGen, type CharacterGen } from '../lib/characterGen'
import {
  classifyMessage,
  dispatchToWebhooks,
  synthesizeResponse,
  callBotWebhook,
  recommendFood,
  selectFood,
  sendFeedback,
  type Restaurant,
  type WeatherData,
  type MenuItem,
  type EmailItem,
  type ClassifyResult,
  type IntentPath,
  type CombinedResponse,
} from '../lib/n8n'
import { supabase } from '../lib/supabase'
import { getTodayDiary, computeTamagotchiStats } from '../lib/db'

// ── 타입 ──────────────────────────────────────────────────────────

interface Message {
  id: number
  role: 'user' | 'bot'
  text: string
  restaurants?: Restaurant[]
  weather?: WeatherData[]
  emails?: EmailItem[]
  classified?: string[]
  failed?: string[]
  food_path?: IntentPath
  food_description?: string
}

interface Tamagotchi { hp: number; hunger: number; mood: number }

interface MenuState {
  restaurant: Restaurant
  menus: MenuItem[]
  loading: boolean
  selected: string | null
}

interface PendingDiaryUpdate {
  existingId: string
  existingSummary: string
  userId: string
  message: string
  classified: ClassifyResult
}

// ── 유틸 ──────────────────────────────────────────────────────────

function getMealType(profile: {
  breakfast_time?: string | null
  lunch_time?: string | null
  dinner_time?: string | null
  snack_time?: string | null
}): string {
  const now = new Date()
  const current = now.getHours() * 60 + now.getMinutes()
  const toMin = (t?: string | null) => {
    if (!t) return null
    const [h, m] = t.split(':').map(Number)
    return h * 60 + m
  }
  const meals: [number, string][] = (
    [
      [toMin(profile.breakfast_time), '아침'],
      [toMin(profile.lunch_time), '점심'],
      [toMin(profile.snack_time), '간식'],
      [toMin(profile.dinner_time), '저녁'],
    ] as [number | null, string][]
  )
    .filter((e): e is [number, string] => e[0] !== null)
    .sort(([a], [b]) => a - b)

  let result = '간식'
  for (const [t, label] of meals) {
    if (current >= t) result = label
  }
  return result
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────

type EvoState = 'checking' | 'no_worldcup' | 'cube' | 'evolved'

const CHAT_KEY = 'mukgoorm_chat'
const CHAR_GEN_CACHE_KEY = 'mukgoorm_chargen'

function loadCharGenCache(): { evoState: EvoState; charGen: CharacterGen | null; tamagotchi: Tamagotchi | null } {
  try {
    const raw = localStorage.getItem(CHAR_GEN_CACHE_KEY)
    if (!raw) return { evoState: 'checking', charGen: null, tamagotchi: null }
    const { evoState, charGen, tamagotchi } = JSON.parse(raw)
    return { evoState: evoState ?? 'checking', charGen: charGen ?? null, tamagotchi: tamagotchi ?? null }
  } catch {
    return { evoState: 'checking', charGen: null, tamagotchi: null }
  }
}

function saveCharGenCache(userId: string, evoState: EvoState, charGen: CharacterGen | null) {
  try {
    localStorage.setItem(CHAR_GEN_CACHE_KEY, JSON.stringify({ userId, evoState, charGen }))
  } catch {}
}

function preloadCharGenImages(gen: CharacterGen) {
  [gen.normal_url, gen.happy_url, gen.tired_url, gen.eating_url]
    .filter(Boolean)
    .forEach(url => { new Image().src = url! })
}

function loadCachedMessages(): Message[] {
  try {
    const raw = sessionStorage.getItem(CHAT_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export default function Home() {
  const { user, profile } = useUser()
  const [tamagotchi, setTamagotchi] = useState<Tamagotchi | null>(() => loadCharGenCache().tamagotchi)
  const [messages, setMessages] = useState<Message[]>(loadCachedMessages)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [showDiaryModal, setShowDiaryModal] = useState(false)
  const [pendingDiary, setPendingDiary] = useState<PendingDiaryUpdate | null>(null)
  const [menuState, setMenuState] = useState<MenuState | null>(null)
  const [evoState, setEvoState] = useState<EvoState>(() => loadCharGenCache().evoState)
  const [charGen, setCharGen] = useState<CharacterGen | null>(() => loadCharGenCache().charGen)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (profile && messages.length === 0) {
      setMessages([{ id: 0, role: 'bot', text: `안녕! 나 ${profile.tamagotchi_name}이야 🌧️ 오늘 뭐 먹었어?` }])
    }
  }, [profile?.tamagotchi_name])

  useEffect(() => {
    if (messages.length > 0) {
      sessionStorage.setItem(CHAT_KEY, JSON.stringify(messages))
    }
  }, [messages])

  useEffect(() => {
    if (!user) return
    computeTamagotchiStats(user.id).then(setTamagotchi)

    ;(async () => {
      try {
        const raw = localStorage.getItem(CHAR_GEN_CACHE_KEY)
        if (raw) {
          const { userId } = JSON.parse(raw)
          if (userId !== user.id) {
            setEvoState('checking')
            setCharGen(null)
            localStorage.removeItem(CHAR_GEN_CACHE_KEY)
          }
        }
      } catch {}

      const { data: session } = await supabase
        .from('worldcup_sessions')
        .select('created_at')
        .eq('user_id', user.id)
        .eq('completed', true)
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle()

      if (!session) {
        setEvoState('no_worldcup')
        saveCharGenCache(user.id, 'no_worldcup', null)
        return
      }

      const gen = await getCharacterGen(user.id)
      setCharGen(gen)
      const newEvoState: EvoState = gen?.status === 'done' ? 'evolved' : 'cube'
      setEvoState(newEvoState)
      saveCharGenCache(user.id, newEvoState, gen)
    })()
  }, [user])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!loading) { setElapsed(0); return }
    const t = setInterval(() => setElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [loading])

  useEffect(() => {
    if (!user || !tamagotchi) return
    try {
      const raw = localStorage.getItem(CHAR_GEN_CACHE_KEY)
      if (!raw) return
      const cache = JSON.parse(raw)
      if (cache.userId === user.id) {
        localStorage.setItem(CHAR_GEN_CACHE_KEY, JSON.stringify({ ...cache, tamagotchi }))
      }
    } catch {}
  }, [tamagotchi, user])

  useEffect(() => {
    if (charGen) preloadCharGenImages(charGen)
  }, [charGen])

  const characterImage = (() => {
    if (evoState === 'checking') return '/cube.png'
    if (evoState === 'no_worldcup') return '/cube.png'
    if (evoState === 'cube') return '/cube.png'
    const generated = {
      normal: charGen?.normal_url,
      happy:  charGen?.happy_url,
      tired:  charGen?.tired_url,
      eating: charGen?.eating_url,
    }
    return tamagotchi
      ? selectCharacterImage('none', tamagotchi.hunger, tamagotchi.mood, tamagotchi.hp, generated)
      : (charGen?.normal_url ?? '/normal.png')
  })()

  // ── 메시지 전송 ──────────────────────────────────────────────

  async function handleSend() {
    if (!input.trim() || loading || !profile) return
    const text = input.trim()
    setInput('')
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text }])
    setLoading(true)

    try {
      const classified = await classifyMessage(text)

      let diaryConflict: { id: string; summary: string } | null = null
      if (classified.bots.includes('일기')) {
        diaryConflict = await getTodayDiary(profile.user_id, classified.date)
      }

      const hasFood = classified.bots.includes('음식추천')
      const nonFoodClassified = { ...classified, bots: classified.bots.filter(b => b !== '음식추천') }

      const [dispatchResult, foodResult] = await Promise.allSettled([
        nonFoodClassified.bots.length > 0
          ? dispatchToWebhooks(profile.user_id, text, nonFoodClassified, {
              city: profile.city ?? '',
              village: profile.village ?? '',
              meal_type: getMealType(profile),
            })
          : Promise.resolve<CombinedResponse>({ messages: [], restaurants: [], weather: [], emails: [], failed: [] }),
        hasFood
          ? recommendFood({
              user_id: profile.user_id,
              message: text,
              location: profile.village ?? '',
              date: classified.date,
            })
          : Promise.resolve(null),
      ])

      const combined: CombinedResponse = dispatchResult.status === 'fulfilled'
        ? dispatchResult.value
        : { messages: [], restaurants: [], weather: [], emails: [], failed: [...nonFoodClassified.bots] }

      if (hasFood) {
        if (foodResult.status === 'fulfilled' && foodResult.value) {
          const food = foodResult.value
          combined.messages.push(food.message)
          combined.restaurants.push(...food.restaurants)
          combined.food_path = food.path
          combined.food_description = food.description
        } else {
          combined.failed.push('음식추천')
        }
      }

      const reply = await synthesizeResponse(
        profile.tamagotchi_name ?? '먹구름',
        text, classified, combined,
      )

      const botMsg: Message = {
        id: Date.now() + 1,
        role: 'bot',
        text: reply,
        restaurants: combined.restaurants.length > 0 ? combined.restaurants : undefined,
        weather: combined.weather.length > 0 ? combined.weather : undefined,
        emails: combined.emails.length > 0 ? combined.emails : undefined,
        classified: classified.bots,
        failed: combined.failed.length > 0 ? combined.failed : undefined,
        food_path: combined.food_path,
        food_description: combined.food_description,
      }
      setMessages(prev => [...prev, botMsg])

      if (diaryConflict) {
        setPendingDiary({
          existingId: diaryConflict.id,
          existingSummary: diaryConflict.summary,
          userId: profile.user_id,
          message: text,
          classified,
        })
        setShowDiaryModal(true)
      }

      if (user) {
        computeTamagotchiStats(user.id).then(setTamagotchi)
      }
    } catch {
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'bot', text: '앗, 뭔가 잘못됐어 😥 다시 말해줄래?' }])
    } finally {
      setLoading(false)
    }
  }

  async function handleRestaurantFeedback(restaurant: Restaurant, feedback: 'like' | 'dislike') {
    if (!profile) return
    try {
      await sendFeedback({
        user_id: profile.user_id,
        restaurant_id: restaurant.restaurant_id,
        food_name: restaurant.food_name,
        category: restaurant.category,
        feedback,
      })
    } catch { /* silent */ }
  }

  function handleMenuRequest(restaurant: Restaurant) {
    setMenuState({
      restaurant,
      menus: restaurant.menus ?? [],
      loading: false,
      selected: null,
    })
  }

  async function handleMenuSelect(menuName: string) {
    if (!menuState || !profile) return
    const { restaurant } = menuState
    const selectedMenu = menuState.menus.find(m => m.menu_name === menuName)
    setMenuState(prev => prev ? { ...prev, selected: menuName } : null)

    try {
      await selectFood({
        user_id: profile.user_id,
        restaurant_id: restaurant.restaurant_id,
        menu_name: menuName,
        keywords: selectedMenu?.keywords ?? [],
        location: profile.village ?? '',
        date: new Date().toISOString().slice(0, 10),
      })
      setMenuState(null)
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'bot',
        text: `${restaurant.food_name}에서 ${menuName} 선택했구나 🍽️ 맛있게 먹어!`,
      }])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'bot',
        text: '기록 저장에 실패했어 😥',
      }])
    }
  }

  async function handleDiaryOverwrite() {
    if (!pendingDiary) return
    setShowDiaryModal(false)
    try {
      await callBotWebhook(
        '/webhook/diary',
        pendingDiary.userId,
        pendingDiary.message,
        pendingDiary.classified,
        { is_update: true, diary_id: pendingDiary.existingId },
      )
      setMessages(prev => [...prev, { id: Date.now(), role: 'bot', text: '오늘 일기를 새 내용으로 덮어썼어 📝' }])
    } catch {
      setMessages(prev => [...prev, { id: Date.now(), role: 'bot', text: '일기 수정 실패했어 😥 n8n 연결을 확인해줘' }])
    } finally {
      setPendingDiary(null)
    }
  }

  // ── 렌더 ─────────────────────────────────────────────────────

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 42px)', maxWidth: 680, margin: '0 auto' }}>

      {/* 캐릭터 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-5)', padding: '10px 0 var(--sp-3)' }}>
        <img src={characterImage} alt="캐릭터" style={{ width: 128, height: 128, objectFit: 'contain', imageRendering: 'pixelated', flexShrink: 0 }} />
        <div>
          <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)' }}>{profile?.tamagotchi_name}의 오늘</div>
          <div style={{ color: 'var(--text-strong)', fontSize: 'var(--fs-md)', marginTop: 4 }}>
            {loading
              ? '생각 중...'
              : evoState === 'checking'
                ? '불러오는 중...'
                : evoState === 'no_worldcup'
                  ? '월드컵을 완료해야 캐릭터가 태어나요 🥚'
                  : evoState === 'cube'
                    ? 'AI가 나만의 캐릭터를 만드는 중... 🌀'
                    : '날씨, 식사, 일정, 맛집 뭐든지 물어봐 🌧️'}
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: 1, background: 'var(--border)', marginBottom: 'var(--sp-4)' }} />

      {/* 채팅 영역 */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)', paddingBottom: 'var(--sp-2)' }}>
        {messages.map(msg => (
          <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '78%',
              padding: 'var(--sp-3) var(--sp-4)',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              background: msg.role === 'user' ? 'var(--accent)' : 'var(--surface)',
              color: msg.role === 'user' ? 'var(--text-on-accent)' : 'var(--text)',
              border: msg.role === 'user' ? 'none' : '1px solid var(--border)',
              boxShadow: 'var(--shadow-sm)',
              fontSize: 'var(--fs-base)', lineHeight: 'var(--lh-base)', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {msg.text}
            </div>

            {/* 분류 태그 */}
            {msg.role === 'bot' && msg.classified && msg.classified.length > 0 && (
              <div style={{ display: 'flex', gap: 'var(--sp-1)', marginTop: 6, flexWrap: 'wrap' }}>
                {msg.classified.map(bot => (
                  <span key={bot} style={{
                    fontSize: 'var(--fs-xs)', padding: '2px var(--sp-2)', borderRadius: 'var(--radius-pill)',
                    background: 'var(--accent-soft)', color: 'var(--accent-ink)',
                  }}>{bot}</span>
                ))}
              </div>
            )}

            {/* 실패 태그 */}
            {msg.role === 'bot' && msg.failed && msg.failed.length > 0 && (
              <div style={{ display: 'flex', gap: 'var(--sp-1)', marginTop: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger)' }}>⚠️ 연결 실패:</span>
                {msg.failed.map(bot => (
                  <span key={bot} style={{
                    fontSize: 'var(--fs-xs)', padding: '2px var(--sp-2)', borderRadius: 'var(--radius-pill)',
                    background: 'var(--danger-soft)', color: 'var(--danger)',
                  }}>{bot}</span>
                ))}
              </div>
            )}

            {/* 날씨 카드 */}
            {msg.weather && msg.weather.length > 0 && (
              <div style={{ marginTop: 10, width: '100%', display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
                {msg.weather.map((w, i) => <WeatherCard key={i} weather={w} />)}
              </div>
            )}

            {/* 이메일 카드 */}
            {msg.emails && msg.emails.length > 0 && (
              <div style={{ marginTop: 10, width: '100%', display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
                {msg.emails.map((e, i) => <EmailCard key={i} email={e} />)}
              </div>
            )}

            {/* 음식 추천 경로 */}
            {msg.food_description && (
              <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)', marginTop: 6, paddingLeft: 2 }}>
                {msg.food_path === 'A' && '🎯 '}
                {msg.food_path === 'B' && '🔍 '}
                {msg.food_path === 'C' && '✨ '}
                {msg.food_description}
              </div>
            )}

            {/* 식당 카드 */}
            {msg.restaurants && msg.restaurants.length > 0 && (
              <div style={{ marginTop: 10, width: '100%', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--sp-3)' }}>
                {msg.restaurants.map((r, i) => (
                  <RestaurantCard
                    key={i}
                    restaurant={r}
                    onMenuRequest={handleMenuRequest}
                    onFeedback={handleRestaurantFeedback}
                    isMenuOpen={menuState?.restaurant.restaurant_id === r.restaurant_id}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <LoadingBubble elapsed={elapsed} />}
        <div ref={bottomRef} />
      </div>

      {/* 메뉴 패널 */}
      {menuState && (
        <MenuPanel
          state={menuState}
          onMenuSelect={handleMenuSelect}
          onClose={() => setMenuState(null)}
        />
      )}

      {/* 일기 덮어쓰기 모달 */}
      {showDiaryModal && pendingDiary && (
        <ModalOverlay>
          <div style={{
            background: 'var(--surface)', borderRadius: 'var(--radius-xl)', padding: 28,
            width: 340, display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)',
            boxShadow: 'var(--shadow-lg)',
          }}>
            <h3 style={{ color: 'var(--text-strong)', margin: 0, fontSize: 'var(--fs-md)' }}>오늘 일기가 이미 있어 📖</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', margin: 0, lineHeight: 'var(--lh-base)' }}>
              기존 요약: <span style={{ color: 'var(--text)' }}>{pendingDiary.existingSummary}</span><br />
              새 내용으로 덮어쓸까?
            </p>
            <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
              <GhostBtn onClick={() => { setShowDiaryModal(false); setPendingDiary(null) }}>취소</GhostBtn>
              <PrimaryBtn onClick={handleDiaryOverwrite}>덮어쓰기</PrimaryBtn>
            </div>
          </div>
        </ModalOverlay>
      )}

      {/* 입력창 */}
      <div style={{ display: 'flex', gap: 'var(--sp-2)', paddingTop: 'var(--sp-3)', paddingBottom: 'var(--sp-2)' }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder="오늘 뭐 먹었어? 날씨는? 맛집 추천해줘!"
          disabled={loading}
          style={{
            flex: 1, background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-pill)', padding: 'var(--sp-3) var(--sp-5)',
            color: 'var(--text)', fontSize: 'var(--fs-base)', outline: 'none',
            boxShadow: 'var(--shadow-sm)',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            background: 'var(--accent)', border: 'none', borderRadius: 'var(--radius-pill)',
            padding: 'var(--sp-3) var(--sp-5)', color: 'var(--text-on-accent)',
            fontSize: 'var(--fs-base)', fontWeight: 'var(--fw-bold)',
            cursor: 'pointer', opacity: loading || !input.trim() ? 0.5 : 1,
            boxShadow: 'var(--shadow-accent)', transition: 'var(--transition)',
          }}
        >전송</button>
      </div>
    </div>
  )
}

// ── 서브 컴포넌트 ─────────────────────────────────────────────────

function RestaurantCard({
  restaurant: r,
  onMenuRequest,
  onFeedback,
  isMenuOpen,
}: {
  restaurant: Restaurant
  onMenuRequest: (r: Restaurant) => void
  onFeedback: (r: Restaurant, feedback: 'like' | 'dislike') => void
  isMenuOpen: boolean
}) {
  const [voted, setVoted] = useState<'like' | 'dislike' | null>(null)

  function handleVote(f: 'like' | 'dislike') {
    if (voted) return
    setVoted(f)
    onFeedback(r, f)
  }

  return (
    <div style={{
      background: isMenuOpen ? 'var(--accent-soft)' : 'var(--surface)',
      border: `1px solid ${isMenuOpen ? 'var(--accent)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-lg)', padding: 'var(--sp-4)',
      display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)',
      boxShadow: isMenuOpen ? 'var(--shadow-accent)' : 'var(--shadow-sm)',
      transition: 'var(--transition)',
    }}>
      <div style={{ fontWeight: 'var(--fw-bold)', fontSize: 'var(--fs-base)', color: 'var(--text-strong)' }}>{r.food_name}</div>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--accent-ink)' }}>{r.category}</div>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)' }}>{r.location}</div>
      {r.description && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text)', lineHeight: 'var(--lh-base)', marginTop: 2 }}>{r.description}</div>}
      {r.reason && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)', fontStyle: 'italic' }}>{r.reason}</div>}
      {r.phone && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-faint)' }}>📞 {r.phone}</div>}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'var(--sp-2)' }}>
        <button
          onClick={() => onMenuRequest(r)}
          style={{
            background: isMenuOpen ? 'var(--accent)' : 'var(--surface-2)',
            border: 'none', borderRadius: 'var(--radius-sm)', padding: 'var(--sp-1) var(--sp-3)',
            color: isMenuOpen ? 'var(--text-on-accent)' : 'var(--text)', fontSize: 'var(--fs-xs)',
            cursor: 'pointer', fontWeight: 'var(--fw-bold)', transition: 'var(--transition)',
          }}
        >
          {isMenuOpen ? '메뉴 보는 중' : '메뉴 보기 →'}
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {r.link && (
            <a href={r.link} target="_blank" rel="noreferrer" style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-faint)', textDecoration: 'none' }}>
              지도 →
            </a>
          )}
          <button
            onClick={() => handleVote('like')}
            disabled={!!voted}
            style={{
              background: voted === 'like' ? 'var(--success-soft)' : 'none',
              border: `1px solid ${voted === 'like' ? 'var(--success)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-sm)', padding: '4px 8px',
              color: voted === 'like' ? 'var(--success)' : 'var(--text-faint)',
              fontSize: voted === 'like' ? 15 : 13,
              cursor: voted ? 'default' : 'pointer',
              transition: 'var(--transition)',
            }}
          >👍</button>
          <button
            onClick={() => handleVote('dislike')}
            disabled={!!voted}
            style={{
              background: voted === 'dislike' ? 'var(--danger-soft)' : 'none',
              border: `1px solid ${voted === 'dislike' ? 'var(--danger)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-sm)', padding: '4px 8px',
              color: voted === 'dislike' ? 'var(--danger)' : 'var(--text-faint)',
              fontSize: voted === 'dislike' ? 15 : 13,
              cursor: voted ? 'default' : 'pointer',
              transition: 'var(--transition)',
            }}
          >👎</button>
        </div>
      </div>
    </div>
  )
}

function MenuPanel({
  state,
  onMenuSelect,
  onClose,
}: {
  state: MenuState
  onMenuSelect: (menuName: string) => void
  onClose: () => void
}) {
  const { restaurant, menus, loading, selected } = state

  return (
    <div style={{
      position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
      width: 'min(680px, 96vw)',
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--shadow-lg)',
      zIndex: 50, maxHeight: '70vh', display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--sp-4) var(--sp-5)', borderBottom: '1px solid var(--border)' }}>
        <div>
          <div style={{ color: 'var(--text-strong)', fontWeight: 'var(--fw-bold)', fontSize: 'var(--fs-md)' }}>{restaurant.food_name}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-xs)', marginTop: 2 }}>{restaurant.location}</div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-faint)', cursor: 'pointer', fontSize: 20, lineHeight: 1 }}>✕</button>
      </div>

      <div style={{ overflowY: 'auto', flex: 1, padding: 'var(--sp-3) var(--sp-5)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
        {loading && <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-base)', textAlign: 'center', paddingTop: 20 }}>메뉴 불러오는 중...</div>}
        {!loading && menus.length === 0 && (
          <div style={{ color: 'var(--text-faint)', fontSize: 'var(--fs-sm)', textAlign: 'center', paddingTop: 20 }}>등록된 메뉴 정보가 없어요</div>
        )}
        {menus.map(menu => (
          <MenuItemRow
            key={menu.id}
            menu={menu}
            isSelected={selected === menu.menu_name}
            onSelect={() => onMenuSelect(menu.menu_name)}
          />
        ))}
      </div>
    </div>
  )
}

function MenuItemRow({ menu, isSelected, onSelect }: { menu: MenuItem; isSelected: boolean; onSelect: () => void }) {
  return (
    <div style={{
      background: isSelected ? 'var(--accent-soft)' : 'var(--surface-2)',
      border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-md)', padding: 'var(--sp-3) var(--sp-4)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      transition: 'var(--transition)',
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ color: 'var(--text-strong)', fontSize: 'var(--fs-base)', fontWeight: 'var(--fw-bold)' }}>{menu.menu_name}</div>
        {menu.description && <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-xs)', marginTop: 2 }}>{menu.description}</div>}
        <div style={{ display: 'flex', gap: 'var(--sp-1)', marginTop: 4, flexWrap: 'wrap' }}>
          {menu.tags?.map(tag => (
            <span key={tag} style={{ fontSize: 'var(--fs-xs)', padding: '2px var(--sp-2)', borderRadius: 'var(--radius-pill)', background: 'var(--accent-soft)', color: 'var(--accent-ink)' }}>{tag}</span>
          ))}
          {menu.keywords?.map(kw => (
            <span key={kw} style={{ fontSize: 'var(--fs-xs)', padding: '2px var(--sp-2)', borderRadius: 'var(--radius-pill)', background: 'var(--sky-soft)', color: 'var(--sky-ink)' }}>{kw}</span>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 'var(--sp-2)', marginLeft: 'var(--sp-3)' }}>
        {menu.price != null && (
          <div style={{ color: 'var(--text-strong)', fontSize: 'var(--fs-sm)', fontWeight: 'var(--fw-bold)', whiteSpace: 'nowrap' }}>
            {menu.price.toLocaleString()}원
          </div>
        )}
        <button
          onClick={onSelect}
          disabled={isSelected}
          style={{
            background: isSelected ? 'var(--surface-2)' : 'var(--accent)',
            border: 'none', borderRadius: 'var(--radius-sm)', padding: 'var(--sp-1) var(--sp-4)',
            color: isSelected ? 'var(--accent-ink)' : 'var(--text-on-accent)', fontSize: 'var(--fs-xs)',
            cursor: isSelected ? 'default' : 'pointer', fontWeight: 'var(--fw-bold)',
            whiteSpace: 'nowrap', transition: 'var(--transition)',
          }}
        >
          {isSelected ? '선택됨 ✓' : '선택'}
        </button>
      </div>
    </div>
  )
}

function EmailCard({ email: e }: { email: EmailItem }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      onClick={() => setExpanded(v => !v)}
      style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)', padding: 'var(--sp-3) var(--sp-4)',
        cursor: 'pointer', transition: 'var(--transition)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--sp-2)' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 2 }}>
            <span style={{
              fontSize: 10, padding: '1px 6px', borderRadius: 'var(--radius-pill)', fontWeight: 'var(--fw-bold)',
              background: e.is_new ? 'var(--accent)' : 'var(--surface-2)',
              color: e.is_new ? 'var(--text-on-accent)' : 'var(--text-muted)',
              flexShrink: 0,
            }}>
              {e.is_new ? '신규' : '기존'}
            </span>
            <div style={{
              color: 'var(--text-strong)', fontSize: 'var(--fs-sm)', fontWeight: 'var(--fw-medium)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: expanded ? 'normal' : 'nowrap',
            }}>
              {e.subject || '(제목 없음)'}
            </div>
          </div>
          {e.sender && (
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-xs)' }}>
              {e.sender}
            </div>
          )}
        </div>
        <span style={{ color: 'var(--text-faint)', fontSize: 12, flexShrink: 0 }}>{expanded ? '▲' : '▼'}</span>
      </div>
      {expanded && e.summary && (
        <div style={{
          color: 'var(--text)', fontSize: 'var(--fs-xs)', lineHeight: 'var(--lh-base)',
          marginTop: 'var(--sp-2)', paddingTop: 'var(--sp-2)',
          borderTop: '1px solid var(--border)',
        }}>
          {e.summary}
        </div>
      )}
    </div>
  )
}

function WeatherCard({ weather: w }: { weather: WeatherData }) {
  const gradeColor = (grade?: string) =>
    grade === '좋음' ? 'var(--success)' : grade === '보통' ? 'var(--warning)' : grade === '나쁨' ? 'var(--danger)' : 'var(--text-muted)'

  return (
    <div style={{ background: 'var(--surface-sky)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 'var(--sp-4)', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontWeight: 'var(--fw-bold)', fontSize: 'var(--fs-base)', color: 'var(--text-strong)' }}>
        🌤️ 날씨{w.sky && <span style={{ fontWeight: 400, fontSize: 'var(--fs-sm)', color: 'var(--text-muted)', marginLeft: 6 }}>{w.sky}</span>}
      </div>
      <div style={{ display: 'flex', gap: 'var(--sp-4)', flexWrap: 'wrap' }}>
        {w.temperature != null && <span style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-strong)' }}>🌡️ {w.temperature}°C</span>}
        {(w.low_temperature != null || w.high_temperature != null) && (
          <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)' }}>최저 {w.low_temperature ?? '-'}° / 최고 {w.high_temperature ?? '-'}°</span>
        )}
        {w.humidity != null && <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)' }}>💧 {w.humidity}%</span>}
        {w.windSpeed != null && <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)' }}>💨 {w.windSpeed}m/s</span>}
        {w.rain && w.rain !== '없음' && <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--sky-ink)' }}>🌧️ {w.rain}</span>}
      </div>
      {(w.pm10 != null || w.pm25 != null) && (
        <div style={{ display: 'flex', gap: 'var(--sp-3)', flexWrap: 'wrap' }}>
          {w.pm10 != null && <span style={{ fontSize: 'var(--fs-xs)', color: gradeColor(w.pm10_grade) }}>미세먼지 {w.pm10}㎍/m³{w.pm10_grade && ` (${w.pm10_grade})`}</span>}
          {w.pm25 != null && <span style={{ fontSize: 'var(--fs-xs)', color: gradeColor(w.pm25_grade) }}>초미세먼지 {w.pm25}㎍/m³{w.pm25_grade && ` (${w.pm25_grade})`}</span>}
        </div>
      )}
      {w.message && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-muted)', marginTop: 2 }}>{w.message}</div>}
    </div>
  )
}

function LoadingBubble({ elapsed }: { elapsed: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6 }}>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '16px 16px 16px 4px', padding: 'var(--sp-3) var(--sp-5)', display: 'flex', gap: 6, alignItems: 'center', boxShadow: 'var(--shadow-sm)' }}>
        {[0, 1, 2].map(i => (
          <span key={i} style={{
            width: 7, height: 7, borderRadius: '50%', background: 'var(--accent)',
            display: 'inline-block',
            animation: `chatBounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
      {elapsed >= 10 && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-faint)', paddingLeft: 4 }}>맛집 검색 중이면 조금 더 걸릴 수 있어 🍽️</div>}
    </div>
  )
}

function ModalOverlay({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(74, 63, 58, 0.45)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
      {children}
    </div>
  )
}

function GhostBtn({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{ flex: 1, background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: 'var(--sp-3)', color: 'var(--text)', fontSize: 'var(--fs-base)', cursor: 'pointer', transition: 'var(--transition)' }}>
      {children}
    </button>
  )
}

function PrimaryBtn({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{ flex: 1, background: 'var(--accent)', border: 'none', borderRadius: 'var(--radius-sm)', padding: 'var(--sp-3)', color: 'var(--text-on-accent)', fontSize: 'var(--fs-base)', fontWeight: 'var(--fw-bold)', cursor: 'pointer', boxShadow: 'var(--shadow-accent)', transition: 'var(--transition)' }}>
      {children}
    </button>
  )
}
