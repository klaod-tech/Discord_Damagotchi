import { useEffect, useRef, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { selectCharacterImage } from '../lib/image'
import { analyzeIntent } from '../lib/intent'
import { recordMeal } from '../lib/meal'
import { supabase } from '../lib/supabase'

interface Message {
  id: number
  role: 'user' | 'bot'
  text: string
}

interface Tamagotchi {
  hp: number
  hunger: number
  mood: number
}

export default function Home() {
  const { user, profile } = useUser()
  const [tamagotchi, setTamagotchi] = useState<Tamagotchi | null>(null)
  const [messages, setMessages] = useState<Message[]>([
    { id: 0, role: 'bot', text: `안녕! 나 ${profile?.tamagotchi_name ?? '먹구름'}이야 🌧️ 오늘 뭐 먹었어?` },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!user) return
    supabase.from('tamagotchi').select('*').eq('user_id', user.id).maybeSingle()
      .then(({ data }) => { if (data) setTamagotchi(data) })
  }, [user])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (profile) {
      setMessages([{ id: 0, role: 'bot', text: `안녕! 나 ${profile.tamagotchi_name}이야 🌧️ 오늘 뭐 먹었어?` }])
    }
  }, [profile?.tamagotchi_name])

  const characterImage = tamagotchi
    ? selectCharacterImage('none', tamagotchi.hunger, tamagotchi.mood, tamagotchi.hp)
    : '/normal.png'

  async function handleSend() {
    if (!input.trim() || loading || !profile) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text: userMsg }])
    setLoading(true)

    try {
      const result = await analyzeIntent(userMsg, profile.tamagotchi_name)
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'bot', text: result.reply }])

      // 의도별 후속 처리
      if (result.intent === 'meal' && user) {
        const mealResult = await recordMeal(user.id, userMsg, result.entities?.meal_type ?? 'unknown')
        if (mealResult) {
          setMessages(prev => [...prev, {
            id: Date.now() + 2, role: 'bot',
            text: `${mealResult.foodName} 기록했어! 약 ${mealResult.totalCalories}kcal 🍽️`
          }])
          // 타마고치 상태 새로고침
          const { data } = await supabase.from('tamagotchi').select('*').eq('user_id', user.id).maybeSingle()
          if (data) setTamagotchi(data)
        }
      } else if (result.intent === 'weight') {
        setTimeout(() => {
          setMessages(prev => [...prev, {
            id: Date.now() + 2, role: 'bot',
            text: '체중은 왼쪽 ⚖️ 체중 관리에서 기록할 수 있어!'
          }])
        }, 600)
      }
    } catch {
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'bot', text: '앗, 잠깐 문제가 생겼어 😥 다시 말해줘!' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', maxWidth: 640, margin: '0 auto' }}>

      {/* 캐릭터 영역 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, padding: '20px 0 12px' }}>
        <img
          src={characterImage}
          alt="캐릭터"
          style={{ width: 100, height: 100, objectFit: 'contain', imageRendering: 'pixelated', flexShrink: 0 }}
        />
        <div>
          <div style={{ color: '#aaa', fontSize: 13 }}>{profile?.tamagotchi_name}의 오늘</div>
          <div style={{ color: '#fff', fontSize: 15, marginTop: 4 }}>
            {loading ? '...' : '뭐든지 말해봐! 기록해줄게 🌧️'}
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: 1, background: '#2a2a4a', marginBottom: 16 }} />

      {/* 채팅 메시지 */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, paddingBottom: 8 }}>
        {messages.map(msg => (
          <div key={msg.id} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '75%',
              padding: '10px 14px',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              background: msg.role === 'user' ? '#6c63ff' : '#1a1a2e',
              color: '#fff',
              fontSize: 14,
              lineHeight: 1.5,
            }}>
              {msg.text}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex' }}>
            <div style={{ padding: '10px 14px', borderRadius: '16px 16px 16px 4px', background: '#1a1a2e', color: '#666', fontSize: 14 }}>
              ···
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 입력창 */}
      <div style={{ display: 'flex', gap: 8, paddingTop: 12, paddingBottom: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder="오늘 뭐 먹었어? 몸무게는? 일정 있어?"
          disabled={loading}
          style={{
            flex: 1,
            background: '#1a1a2e',
            border: '1px solid #2a2a4a',
            borderRadius: 24,
            padding: '12px 18px',
            color: '#fff',
            fontSize: 14,
            outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            background: '#6c63ff',
            border: 'none',
            borderRadius: 24,
            padding: '12px 20px',
            color: '#fff',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >
          전송
        </button>
      </div>
    </div>
  )
}
