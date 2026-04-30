import { useEffect, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { generateComment } from '../lib/openai'
import { selectCharacterImage } from '../lib/image'
import { supabase } from '../lib/supabase'

interface Tamagotchi {
  hp: number
  hunger: number
  mood: number
  current_image: string
}

export default function Home() {
  const { user, profile } = useUser()
  const [tamagotchi, setTamagotchi] = useState<Tamagotchi | null>(null)
  const [comment, setComment] = useState('')
  const [commentLoading, setCommentLoading] = useState(false)

  useEffect(() => {
    if (!user) return
    supabase
      .from('tamagotchi')
      .select('*')
      .eq('user_id', user.id)
      .single()
      .then(({ data }) => {
        if (data) setTamagotchi(data)
      })
  }, [user])

  useEffect(() => {
    if (!profile || !tamagotchi) return
    setCommentLoading(true)
    const image = selectCharacterImage('none', tamagotchi.hunger, tamagotchi.mood, tamagotchi.hp)
    const prompt = `너는 ${profile.tamagotchi_name}라는 이름의 귀여운 캐릭터야. 지금 상태: hp=${tamagotchi.hp}, 배고픔=${tamagotchi.hunger}, 기분=${tamagotchi.mood}. 오늘 하루 한마디만 짧게 해줘 (20자 이내, 수치는 절대 언급하지 마).`
    generateComment(prompt)
      .then(setComment)
      .finally(() => setCommentLoading(false))
    setTamagotchi(t => t ? { ...t, current_image: image } : t)
  }, [profile, tamagotchi?.hp])

  const image = tamagotchi
    ? selectCharacterImage('none', tamagotchi.hunger, tamagotchi.mood, tamagotchi.hp)
    : '/normal.png'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24, paddingTop: 40 }}>
      <h2 style={{ color: '#aaa', fontSize: 16, margin: 0 }}>
        {profile?.tamagotchi_name}의 오늘
      </h2>

      {/* 캐릭터 이미지 */}
      <div style={{
        background: '#1a1a2e',
        borderRadius: 24,
        padding: 40,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 20,
        width: 280,
      }}>
        <img
          src={image}
          alt="캐릭터"
          style={{ width: 160, height: 160, objectFit: 'contain', imageRendering: 'pixelated' }}
        />

        {/* GPT 대사 */}
        <div style={{
          background: '#16213e',
          borderRadius: 12,
          padding: '12px 16px',
          color: '#fff',
          fontSize: 14,
          textAlign: 'center',
          minHeight: 44,
          lineHeight: 1.5,
        }}>
          {commentLoading ? '...' : comment || '안녕! 오늘도 잘 부탁해 🌧️'}
        </div>
      </div>

      {/* 상태 — 수치 직접 노출 금지, 이미지로만 표현 */}
      {!tamagotchi && (
        <div style={{ color: '#666', fontSize: 13, textAlign: 'center' }}>
          <p>아직 캐릭터 데이터가 없어요.</p>
          <p>식사를 기록하면 캐릭터가 반응하기 시작해요 🍽️</p>
        </div>
      )}
    </div>
  )
}
