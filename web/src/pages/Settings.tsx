import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { updateUserProfile } from '../lib/db'
import { useUser } from '../hooks/useUser'

const ALLERGY_OPTIONS = ['유제품', '글루텐', '견과류', '해산물', '달걀', '돼지고기']
const PREFERENCE_OPTIONS = ['한식', '일식', '중식', '양식', '채식', '고단백']

export default function Settings() {
  const { profile, loading } = useUser()
  const navigate = useNavigate()

  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)

  const [form, setForm] = useState({
    tamagotchi_name: '',
    city: '',
    village: '',
    gender: '',
    age: '',
    height: '',
    init_weight: '',
    goal_weight: '',
    allergies: [] as string[],
    food_preferences: [] as string[],
    wake_time: '',
    breakfast_time: '',
    lunch_time: '',
    dinner_time: '',
    snack_time: '',
    email_provider: '네이버',
    email_address: '',
    email_app_pw: '',
  })

  useEffect(() => {
    if (!profile) return
    setForm({
      tamagotchi_name: profile.tamagotchi_name ?? '',
      city: profile.city ?? '',
      village: profile.village ?? '',
      gender: profile.gender ?? '',
      age: String(profile.age ?? ''),
      height: String(profile.height ?? ''),
      init_weight: String(profile.init_weight ?? ''),
      goal_weight: String(profile.goal_weight ?? ''),
      allergies: profile.allergies ?? [],
      food_preferences: profile.food_preferences ?? [],
      wake_time: profile.wake_time ?? '',
      breakfast_time: profile.breakfast_time ?? '',
      lunch_time: profile.lunch_time ?? '',
      dinner_time: profile.dinner_time ?? '',
      snack_time: profile.snack_time ?? '',
      email_provider: profile.email_provider ?? '네이버',
      email_address: profile.email_address ?? '',
      email_app_pw: '',
    })
  }, [profile])

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

  async function handleSave() {
    if (!profile) return
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      await updateUserProfile(profile.user_id, {
        tamagotchi_name: form.tamagotchi_name,
        city: form.city,
        village: form.village,
        gender: form.gender,
        age: Number(form.age) || null,
        height: Number(form.height) || null,
        init_weight: Number(form.init_weight) || null,
        goal_weight: Number(form.goal_weight) || null,
        allergies: form.allergies,
        food_preferences: form.food_preferences,
        wake_time: form.wake_time,
        breakfast_time: form.breakfast_time,
        lunch_time: form.lunch_time,
        dinner_time: form.dinner_time,
        snack_time: form.snack_time || null,
        email_provider: form.email_provider,
        email_address: form.email_address || null,
        ...(form.email_app_pw ? { email_app_pw: form.email_app_pw } : {}),
        updated_at: new Date().toISOString(),
      })
      sessionStorage.removeItem('mukgoorm_profile')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '저장에 실패했어요.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteAccount() {
    if (!profile) return
    setDeleteLoading(true)
    try {
      // users 테이블 개인정보 삭제 (meal_log, diary 등 ML 데이터는 보존)
      const { error: delError } = await supabase
        .from('users')
        .delete()
        .eq('user_id', profile.user_id)
      if (delError) throw new Error(delError.message)
      sessionStorage.removeItem('mukgoorm_profile')
      await supabase.auth.signOut()
      navigate('/login')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '탈퇴에 실패했어요.')
      setDeleteLoading(false)
    }
  }

  if (loading) {
    return <div style={{ color: '#aaa', padding: 24 }}>로딩 중...</div>
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ color: '#fff', margin: '0 0 24px', fontSize: 20 }}>⚙️ 설정</h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* 기본 정보 */}
        <Section title="기본 정보">
          <Field label="캐릭터 이름">
            <input value={form.tamagotchi_name} onChange={e => set('tamagotchi_name', e.target.value)} style={inputStyle} />
          </Field>
          <Field label="성별">
            <div style={{ display: 'flex', gap: 8 }}>
              <ToggleBtn label="남성" active={form.gender === 'male'} onClick={() => set('gender', 'male')} />
              <ToggleBtn label="여성" active={form.gender === 'female'} onClick={() => set('gender', 'female')} />
            </div>
          </Field>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Field label="나이">
              <input type="number" value={form.age} onChange={e => set('age', e.target.value)} style={inputStyle} />
            </Field>
            <Field label="키 (cm)">
              <input type="number" value={form.height} onChange={e => set('height', e.target.value)} style={inputStyle} />
            </Field>
            <Field label="현재 체중 (kg)">
              <input type="number" value={form.init_weight} onChange={e => set('init_weight', e.target.value)} style={inputStyle} />
            </Field>
            <Field label="목표 체중 (kg)">
              <input type="number" value={form.goal_weight} onChange={e => set('goal_weight', e.target.value)} style={inputStyle} />
            </Field>
          </div>
        </Section>

        {/* 위치 */}
        <Section title="📍 위치">
          <p style={{ color: '#555', fontSize: 12, margin: 0 }}>날씨 및 맛집 추천 기준 위치. "집 근처 맛집" 같은 요청에 사용돼요.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Field label="도시">
              <input placeholder="예: 서울" value={form.city} onChange={e => set('city', e.target.value)} style={inputStyle} />
            </Field>
            <Field label="동 주소">
              <input placeholder="예: 역삼동" value={form.village} onChange={e => set('village', e.target.value)} style={inputStyle} />
            </Field>
          </div>
        </Section>

        {/* 식단 */}
        <Section title="🥗 식단 설정">
          <Field label="알레르기">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {ALLERGY_OPTIONS.map(opt => (
                <TagBtn key={opt} label={opt} active={form.allergies.includes(opt)} onClick={() => toggleArray('allergies', opt)} />
              ))}
            </div>
          </Field>
          <Field label="음식 선호도">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {PREFERENCE_OPTIONS.map(opt => (
                <TagBtn key={opt} label={opt} active={form.food_preferences.includes(opt)} onClick={() => toggleArray('food_preferences', opt)} />
              ))}
            </div>
          </Field>
        </Section>

        {/* 시간 설정 */}
        <Section title="⏰ 시간 설정">
          {[
            { label: '기상 시간', key: 'wake_time', required: true },
            { label: '아침 식사', key: 'breakfast_time', required: true },
            { label: '점심 식사', key: 'lunch_time', required: true },
            { label: '저녁 식사', key: 'dinner_time', required: true },
            { label: '간식 시간', key: 'snack_time', required: false },
          ].map(({ label, key, required }) => (
            <Field key={key} label={label + (!required ? ' (선택)' : '')}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input
                  type="time"
                  value={form[key as keyof typeof form] as string}
                  onChange={e => set(key, e.target.value)}
                  style={{ ...inputStyle, flex: 1 }}
                />
                {!required && form[key as keyof typeof form] && (
                  <button
                    onClick={() => set(key, '')}
                    style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}
                  >✕</button>
                )}
              </div>
            </Field>
          ))}
        </Section>

        {/* 이메일 */}
        <Section title="📧 이메일 설정 (선택)">
          <Field label="이메일 제공사">
            <div style={{ display: 'flex', gap: 8 }}>
              {['네이버', '구글', '다음'].map(p => (
                <ToggleBtn key={p} label={p} active={form.email_provider === p} onClick={() => set('email_provider', p)} />
              ))}
            </div>
          </Field>
          <Field label="이메일 주소">
            <input type="email" value={form.email_address} onChange={e => set('email_address', e.target.value)} style={inputStyle} />
          </Field>
          <Field label="앱 비밀번호">
            <input type="password" value={form.email_app_pw} onChange={e => set('email_app_pw', e.target.value)} placeholder="변경 시에만 입력" style={inputStyle} />
          </Field>
        </Section>

        {/* 저장 */}
        {error && <p style={{ color: '#ff6b6b', fontSize: 13, margin: 0 }}>{error}</p>}
        {saved && <p style={{ color: '#4caf50', fontSize: 13, margin: 0 }}>✓ 저장되었어요!</p>}
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            background: saving ? '#2a2a4a' : '#6c63ff',
            color: saving ? '#555' : '#fff',
            border: 'none', borderRadius: 8,
            padding: '14px', fontSize: 14, fontWeight: 600,
            cursor: saving ? 'not-allowed' : 'pointer',
          }}
        >
          {saving ? '저장 중...' : '저장하기'}
        </button>

        {/* 계정 관리 */}
        <Section title="🗑️ 계정 관리">
          <p style={{ color: '#555', fontSize: 13, margin: 0, lineHeight: 1.7 }}>
            회원 탈퇴 시 이름, 위치, 신체 정보 등 개인정보는 즉시 삭제돼요.<br />
            식사 기록, 일기, 일정 등은 서비스 개선을 위해 익명으로 보존될 수 있어요.
          </p>
          <button
            onClick={() => setShowDeleteModal(true)}
            style={{
              background: 'transparent',
              border: '1px solid #3a1a1a',
              borderRadius: 8, padding: '12px 20px',
              color: '#ff6b6b', fontSize: 14, cursor: 'pointer',
              alignSelf: 'flex-start',
            }}
          >
            회원 탈퇴
          </button>
        </Section>
      </div>

      {/* 탈퇴 확인 모달 */}
      {showDeleteModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }}>
          <div style={{
            background: '#1a1a2e', borderRadius: 16, padding: 32,
            width: 360, display: 'flex', flexDirection: 'column', gap: 16,
            boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          }}>
            <h3 style={{ color: '#fff', margin: 0, fontSize: 18 }}>정말 탈퇴할까요?</h3>
            <p style={{ color: '#aaa', fontSize: 13, margin: 0, lineHeight: 1.7 }}>
              개인정보(이름, 위치, 신체 정보, 이메일)는 즉시 삭제돼요.<br />
              식사 기록 등 다른 데이터는 익명으로 보존돼요.<br />
              <strong style={{ color: '#ff6b6b' }}>이 작업은 되돌릴 수 없어요.</strong>
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setShowDeleteModal(false)}
                style={{
                  flex: 1, background: '#16213e', border: 'none',
                  borderRadius: 8, padding: 12,
                  color: '#fff', fontSize: 14, cursor: 'pointer',
                }}
              >취소</button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleteLoading}
                style={{
                  flex: 1, background: '#c62828', border: 'none',
                  borderRadius: 8, padding: 12,
                  color: '#fff', fontSize: 14, fontWeight: 600,
                  cursor: deleteLoading ? 'not-allowed' : 'pointer',
                }}
              >
                {deleteLoading ? '처리 중...' : '탈퇴하기'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: '#1a1a2e', borderRadius: 12, padding: 24,
      display: 'flex', flexDirection: 'column', gap: 16,
    }}>
      <h3 style={{ color: '#fff', margin: 0, fontSize: 15, fontWeight: 600 }}>{title}</h3>
      {children}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{ color: '#aaa', fontSize: 13 }}>{label}</label>
      {children}
    </div>
  )
}

function ToggleBtn({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      border: '1px solid #2a2a4a', borderRadius: 8, padding: '9px 16px',
      color: '#fff', fontSize: 13, cursor: 'pointer',
      background: active ? '#6c63ff' : '#16213e',
    }}>{label}</button>
  )
}

function TagBtn({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      border: '1px solid #2a2a4a', borderRadius: 20, padding: '6px 14px',
      color: '#fff', fontSize: 13, cursor: 'pointer',
      background: active ? '#6c63ff' : '#16213e',
    }}>{label}</button>
  )
}

const inputStyle: React.CSSProperties = {
  background: '#16213e', border: '1px solid #2a2a4a', borderRadius: 8,
  padding: '10px 14px', color: '#fff', fontSize: 14, outline: 'none',
  width: '100%', boxSizing: 'border-box',
}
