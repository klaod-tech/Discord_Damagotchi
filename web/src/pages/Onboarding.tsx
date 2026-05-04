import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { createUserProfile } from '../lib/db'

const STEPS = ['캐릭터', '위치', '신체·식단', '시간설정', '이메일']

export default function Onboarding() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    tamagotchi_name: '',
    city: '',
    village: '',
    gender: '',
    age: '',
    height: '',
    goal_weight: '',
    allergies: [] as string[],
    food_preferences: [] as string[],
    wake_time: '07:00',
    breakfast_time: '08:00',
    lunch_time: '12:00',
    dinner_time: '19:00',
    snack_time: '15:00',
    email_provider: '네이버',
    email_address: '',
    email_app_pw: '',
  })

  function set(key: string, value: string) {
    setForm(f => ({ ...f, [key]: value }))
  }

  function toggleArray(key: 'allergies' | 'food_preferences', value: string) {
    setForm(f => ({
      ...f,
      [key]: f[key].includes(value)
        ? f[key].filter(v => v !== value)
        : [...f[key], value],
    }))
  }

  async function handleFinish() {
    setLoading(true)
    setError('')
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) { setError('로그인 정보가 없어요.'); setLoading(false); return }

    try {
      await createUserProfile({
        user_id: user.id,
        tamagotchi_name: form.tamagotchi_name,
        city: form.city,
        village: form.village,
        gender: form.gender,
        age: Number(form.age),
        height: Number(form.height),
        goal_weight: Number(form.goal_weight),
        allergies: form.allergies,
        food_preferences: form.food_preferences,
        wake_time: form.wake_time,
        breakfast_time: form.breakfast_time,
        lunch_time: form.lunch_time,
        dinner_time: form.dinner_time,
        snack_time: form.snack_time,
        email_provider: form.email_provider,
        email_address: form.email_address,
        email_app_pw: form.email_app_pw,
      })
      navigate('/')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : JSON.stringify(e))
    } finally {
      setLoading(false)
    }
  }

  const ALLERGY_OPTIONS = ['유제품', '글루텐', '견과류', '해산물', '달걀', '돼지고기']
  const PREFERENCE_OPTIONS = ['한식', '일식', '중식', '양식', '채식', '고단백']

  return (
    <div style={{ minHeight: '100vh', background: '#0f0f23', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ background: '#1a1a2e', borderRadius: 16, padding: 40, width: 420, display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* 진행 바 */}
        <div style={{ display: 'flex', gap: 6 }}>
          {STEPS.map((_, i) => (
            <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: i <= step ? '#6c63ff' : '#2a2a4a' }} />
          ))}
        </div>

        <div>
          <h2 style={{ color: '#fff', margin: '0 0 4px', fontSize: 20 }}>
            {step === 0 && '🐾 캐릭터 이름을 정해줘요'}
            {step === 1 && '📍 어디에 살고 있어요?'}
            {step === 2 && '⚖️ 신체 정보 & 식단'}
            {step === 3 && '⏰ 하루 일정을 알려줘요'}
            {step === 4 && '📧 이메일 설정 (선택)'}
          </h2>
          <p style={{ color: '#aaa', margin: 0, fontSize: 13 }}>{STEPS[step]} 단계 ({step + 1}/{STEPS.length})</p>
        </div>

        {/* 단계별 입력 */}
        {step === 0 && (
          <input
            placeholder="캐릭터 이름 (예: 뭉치)"
            value={form.tamagotchi_name}
            onChange={e => set('tamagotchi_name', e.target.value)}
            style={inputStyle}
          />
        )}

        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <input placeholder="도시 (예: 서울)" value={form.city} onChange={e => set('city', e.target.value)} style={inputStyle} />
            <input placeholder="동 단위 주소 (예: 역삼동)" value={form.village} onChange={e => set('village', e.target.value)} style={inputStyle} />
            <p style={{ color: '#888', fontSize: 12, margin: 0 }}>도시는 날씨, 동 주소는 음식 추천에 사용돼요.</p>
          </div>
        )}

        {step === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => set('gender', 'male')} style={{ ...genderBtn, background: form.gender === 'male' ? '#6c63ff' : '#16213e' }}>남성</button>
              <button onClick={() => set('gender', 'female')} style={{ ...genderBtn, background: form.gender === 'female' ? '#6c63ff' : '#16213e' }}>여성</button>
            </div>
            <input placeholder="나이" type="number" value={form.age} onChange={e => set('age', e.target.value)} style={inputStyle} />
            <input placeholder="키 (cm)" type="number" value={form.height} onChange={e => set('height', e.target.value)} style={inputStyle} />
            <input placeholder="목표 체중 (kg)" type="number" value={form.goal_weight} onChange={e => set('goal_weight', e.target.value)} style={inputStyle} />

            <div>
              <p style={{ color: '#aaa', fontSize: 13, margin: '0 0 8px' }}>알레르기 (복수 선택)</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {ALLERGY_OPTIONS.map(opt => (
                  <button key={opt} onClick={() => toggleArray('allergies', opt)} style={{ ...tagBtn, background: form.allergies.includes(opt) ? '#6c63ff' : '#16213e' }}>{opt}</button>
                ))}
              </div>
            </div>

            <div>
              <p style={{ color: '#aaa', fontSize: 13, margin: '0 0 8px' }}>음식 선호도 (복수 선택)</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {PREFERENCE_OPTIONS.map(opt => (
                  <button key={opt} onClick={() => toggleArray('food_preferences', opt)} style={{ ...tagBtn, background: form.food_preferences.includes(opt) ? '#6c63ff' : '#16213e' }}>{opt}</button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              { label: '기상 시간', key: 'wake_time' },
              { label: '아침 식사', key: 'breakfast_time' },
              { label: '점심 식사', key: 'lunch_time' },
              { label: '저녁 식사', key: 'dinner_time' },
              { label: '간식 시간', key: 'snack_time' },
            ].map(({ label, key }) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ color: '#aaa', fontSize: 13, width: 80 }}>{label}</span>
                <input type="time" value={form[key as keyof typeof form] as string} onChange={e => set(key, e.target.value)} style={{ ...inputStyle, flex: 1 }} />
              </div>
            ))}
          </div>
        )}

        {step === 4 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <p style={{ color: '#888', fontSize: 12, margin: 0 }}>이메일 알림을 받으려면 입력해요. 나중에 설정에서도 변경 가능해요.</p>
            <div style={{ display: 'flex', gap: 8 }}>
              {['네이버', '구글', '다음'].map(p => (
                <button key={p} onClick={() => set('email_provider', p)} style={{ ...genderBtn, flex: 1, background: form.email_provider === p ? '#6c63ff' : '#16213e' }}>{p}</button>
              ))}
            </div>
            <input placeholder="이메일 주소" type="email" value={form.email_address} onChange={e => set('email_address', e.target.value)} style={inputStyle} />
            <input placeholder="앱 비밀번호" type="password" value={form.email_app_pw} onChange={e => set('email_app_pw', e.target.value)} style={inputStyle} />
            <p style={{ color: '#555', fontSize: 11, margin: 0 }}>앱 비밀번호: 네이버 → 보안설정 → 2단계 인증 → 앱 비밀번호</p>
          </div>
        )}

        {error && <p style={{ color: '#ff6b6b', fontSize: 13, margin: 0 }}>{error}</p>}

        <div style={{ display: 'flex', gap: 8 }}>
          {step > 0 && (
            <button onClick={() => setStep(s => s - 1)} style={{ ...buttonStyle, background: '#16213e', flex: 1 }}>이전</button>
          )}
          {step < STEPS.length - 1 ? (
            <button onClick={() => setStep(s => s + 1)} style={{ ...buttonStyle, flex: 1 }}>다음</button>
          ) : (
            <button onClick={handleFinish} disabled={loading} style={{ ...buttonStyle, flex: 1 }}>
              {loading ? '저장 중...' : '시작하기 🎉'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8,
  padding: '12px 16px', color: '#fff', fontSize: 14, outline: 'none',
  width: '100%', boxSizing: 'border-box',
}
const buttonStyle: React.CSSProperties = {
  background: '#6c63ff', border: 'none', borderRadius: 8,
  padding: '12px 16px', color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer',
}
const genderBtn: React.CSSProperties = {
  border: '1px solid #2a2a4a', borderRadius: 8, padding: '12px',
  color: '#fff', fontSize: 14, cursor: 'pointer',
}
const tagBtn: React.CSSProperties = {
  border: '1px solid #2a2a4a', borderRadius: 20, padding: '6px 14px',
  color: '#fff', fontSize: 13, cursor: 'pointer',
}
