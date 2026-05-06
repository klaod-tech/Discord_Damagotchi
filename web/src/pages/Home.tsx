import { useEffect, useRef, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { selectCharacterImage } from '../lib/image'
import { sendToN8N, sendFeedback, type Restaurant } from '../lib/n8n'
import { supabase } from '../lib/supabase'

interface Message {
  id: number
  role: 'user' | 'bot'
  text: string
  restaurants?: Restaurant[]
}

interface Tamagotchi { hp: number; hunger: number; mood: number }

export default function Home() {
  const { user, profile } = useUser()
  const [tamagotchi, setTamagotchi] = useState<Tamagotchi | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (profile) {
      setMessages([{ id: 0, role: 'bot', text: `안녕! 나 ${profile.tamagotchi_name}이야 🌧️ 오늘 뭐 먹었어?` }])
    }
  }, [profile?.tamagotchi_name])

  useEffect(() => {
    if (!user) return
    supabase.from('tamagotchi').select('*').eq('user_id', user.id).maybeSingle()
      .then(({ data }) => { if (data) setTamagotchi(data) })
  }, [user])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!loading) { setElapsed(0); return }
    const t = setInterval(() => setElapsed(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [loading])

  const characterImage = tamagotchi
    ? selectCharacterImage('none', tamagotchi.hunger, tamagotchi.mood, tamagotchi.hp)
    : '/normal.png'

  async function handleSend() {
    if (!input.trim() || loading || !profile) return
    const text = input.trim()
    setInput('')
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', text }])
    setLoading(true)

    try {
      const res = await sendToN8N(profile.user_id, text, {
        city: profile.city ?? '',
        village: profile.village ?? '',
      })
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'bot',
        text: res.message || '응? 다시 말해줘 😅',
        restaurants: res.restaurants,
      }])
      if (user) {
        supabase.from('tamagotchi').select('*').eq('user_id', user.id).maybeSingle()
          .then(({ data }) => { if (data) setTamagotchi(data) })
      }
    } catch {
      setMessages(prev => [...prev, { id: Date.now() + 1, role: 'bot', text: 'n8n 연결을 확인해줘 😥' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', maxWidth: 680, margin: '0 auto' }}>

      <div style={{ display: 'flex', alignItems: 'center', gap: 20, padding: '20px 0 12px' }}>
        <img src={characterImage} alt="캐릭터" style={{ width: 100, height: 100, objectFit: 'contain', imageRendering: 'pixelated', flexShrink: 0 }} />
        <div>
          <div style={{ color: '#aaa', fontSize: 13 }}>{profile?.tamagotchi_name}의 오늘</div>
          <div style={{ color: '#fff', fontSize: 15, marginTop: 4 }}>
            {loading ? '생각 중...' : '날씨, 식사, 일정, 맛집 뭐든지 물어봐 🌧️'}
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: 1, background: '#2a2a4a', marginBottom: 16 }} />

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, paddingBottom: 8 }}>
        {messages.map(msg => (
          <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth: '78%',
              padding: '10px 14px',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              background: msg.role === 'user' ? '#6c63ff' : '#1a1a2e',
              color: '#fff', fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {msg.text}
            </div>
            {msg.restaurants && msg.restaurants.length > 0 && (
              <div style={{ marginTop: 10, width: '100%', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
                {msg.restaurants.map((r, i) => (
                  <RestaurantCard key={i} restaurant={r} userId={profile?.user_id ?? ''} />
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <LoadingBubble elapsed={elapsed} />}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: 'flex', gap: 8, paddingTop: 12, paddingBottom: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          placeholder="오늘 뭐 먹었어? 날씨는? 맛집 추천해줘!"
          disabled={loading}
          style={{
            flex: 1, background: '#1a1a2e', border: '1px solid #2a2a4a',
            borderRadius: 24, padding: '12px 18px', color: '#fff', fontSize: 14, outline: 'none',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            background: '#6c63ff', border: 'none', borderRadius: 24,
            padding: '12px 20px', color: '#fff', fontSize: 14, fontWeight: 600,
            cursor: 'pointer', opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >전송</button>
      </div>
    </div>
  )
}

function RestaurantCard({ restaurant: r, userId }: { restaurant: Restaurant; userId: string }) {
  const [reaction, setReaction] = useState<'like' | 'dislike' | null>(null)

  const handleFeedback = async (type: 'like' | 'dislike') => {
    if (reaction) return
    setReaction(type)
    try {
      await sendFeedback({
        user_id: userId,
        food_name: r.food_name,
        reaction: type,
        location: r.location,
        date: new Date().toISOString().slice(0, 10),
      })
    } catch { /* silent */ }
  }

  return (
    <div style={{ background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 12, padding: 14, display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontWeight: 700, fontSize: 14, color: '#fff' }}>{r.food_name}</div>
      <div style={{ fontSize: 12, color: '#6c63ff' }}>{r.category}</div>
      <div style={{ fontSize: 12, color: '#888' }}>{r.location}</div>
      <div style={{ fontSize: 12, color: '#bbb', lineHeight: 1.5, marginTop: 2 }}>{r.reason}</div>
      {r.rating != null && <div style={{ fontSize: 12, color: '#f5a623' }}>★ {r.rating}</div>}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <FeedbackBtn emoji="👍" active={reaction === 'like'} color="#4caf50" onClick={() => handleFeedback('like')} disabled={!!reaction} />
          <FeedbackBtn emoji="👎" active={reaction === 'dislike'} color="#f44336" onClick={() => handleFeedback('dislike')} disabled={!!reaction} />
        </div>
        {r.link && (
          <a href={r.link} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: '#6c63ff', textDecoration: 'none' }}>
            지도 보기 →
          </a>
        )}
      </div>
    </div>
  )
}

function FeedbackBtn({ emoji, active, color, onClick, disabled }: {
  emoji: string; active: boolean; color: string; onClick: () => void; disabled: boolean
}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      background: active ? color : '#2a2a4a', color: '#fff', border: 'none',
      borderRadius: 6, padding: '4px 10px', cursor: disabled ? 'default' : 'pointer', fontSize: 13,
    }}>{emoji}</button>
  )
}

function LoadingBubble({ elapsed }: { elapsed: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6 }}>
      <div style={{ background: '#1a1a2e', borderRadius: '16px 16px 16px 4px', padding: '12px 18px', display: 'flex', gap: 6, alignItems: 'center' }}>
        {[0, 1, 2].map(i => (
          <span key={i} style={{
            width: 7, height: 7, borderRadius: '50%', background: '#6c63ff',
            display: 'inline-block',
            animation: `chatBounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
      {elapsed >= 10 && (
        <div style={{ fontSize: 11, color: '#555', paddingLeft: 4 }}>맛집 검색 중이면 조금 더 걸릴 수 있어 🍽️</div>
      )}
    </div>
  )
}
