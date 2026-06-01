import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { updateUserProfile } from '../lib/db'
import { useUser } from '../hooks/useUser'

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
      const { data: { session } } = await supabase.auth.getSession()
      const accessToken = session?.access_token ?? ''

      await supabase.auth.signOut({ scope: 'local' })
      sessionStorage.removeItem('mukgoorm_profile')
      localStorage.removeItem('mukgoorm_chargen')

      const { error: delError } = await supabase
        .from('users')
        .delete()
        .eq('user_id', profile.user_id)
      if (delError) throw new Error(delError.message)

      const res = await fetch(
        `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/delete-user`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
          },
        },
      )
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error ?? 'Auth 유저 삭제에 실패했어요.')
      }

      navigate('/login')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '탈퇴에 실패했어요.')
      setDeleteLoading(false)
    }
  }

  if (loading) {
    return <div style={{ color: 'var(--text-muted)', padding: 'var(--sp-6)' }}>로딩 중...</div>
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ color: 'var(--text-strong)', margin: '0 0 var(--sp-6)', fontSize: 'var(--fs-xl)' }}>⚙️ 설정</h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-5)' }}>

        {/* 기본 정보 */}
        <Section title="기본 정보">
          <Field label="캐릭터 이름">
            <input value={form.tamagotchi_name} onChange={e => set('tamagotchi_name', e.target.value)} style={inputStyle} />
          </Field>
          <Field label="성별">
            <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
              <ToggleBtn label="남성" active={form.gender === 'male'} onClick={() => set('gender', 'male')} />
              <ToggleBtn label="여성" active={form.gender === 'female'} onClick={() => set('gender', 'female')} />
            </div>
          </Field>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-3)' }}>
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
          <p style={{ color: 'var(--text-faint)', fontSize: 'var(--fs-xs)', margin: 0 }}>날씨 및 맛집 추천 기준 위치. "집 근처 맛집" 같은 요청에 사용돼요.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-3)' }}>
            <Field label="도시">
              <input placeholder="예: 서울" value={form.city} onChange={e => set('city', e.target.value)} style={inputStyle} />
            </Field>
            <Field label="동 주소">
              <input placeholder="예: 역삼동" value={form.village} onChange={e => set('village', e.target.value)} style={inputStyle} />
            </Field>
          </div>
        </Section>

        {/* 시간 설정 */}
        <Section title="⏰ 시간 설정">
          {[
            { label: '기상 시간', key: 'wake_time' },
            { label: '아침 식사', key: 'breakfast_time' },
            { label: '점심 식사', key: 'lunch_time' },
            { label: '저녁 식사', key: 'dinner_time' },
          ].map(({ label, key }) => (
            <Field key={key} label={label}>
              <input
                type="time"
                value={form[key as keyof typeof form] as string}
                onChange={e => set(key, e.target.value)}
                style={inputStyle}
              />
            </Field>
          ))}
        </Section>

        {/* 이메일 */}
        <Section title="📧 이메일 설정 (선택)">
          <Field label="이메일 제공사">
            <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
              {['네이버', '구글'].map(p => (
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
        {error && <p style={{ color: 'var(--danger)', fontSize: 'var(--fs-sm)', margin: 0 }}>{error}</p>}
        {saved && <p style={{ color: 'var(--success)', fontSize: 'var(--fs-sm)', margin: 0 }}>✓ 저장되었어요!</p>}
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            background: saving ? 'var(--surface-2)' : 'var(--accent)',
            color: saving ? 'var(--text-faint)' : 'var(--text-on-accent)',
            border: 'none', borderRadius: 'var(--radius-pill)',
            padding: 'var(--sp-4)', fontSize: 'var(--fs-base)', fontWeight: 'var(--fw-bold)',
            cursor: saving ? 'not-allowed' : 'pointer',
            boxShadow: saving ? 'none' : 'var(--shadow-accent)',
            transition: 'var(--transition)',
          }}
        >
          {saving ? '저장 중...' : '저장하기'}
        </button>

        {/* 월드컵 재도전 */}
        <Section title="🏆 음식 이상형 월드컵">
          <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', margin: 0, lineHeight: 'var(--lh-base)' }}>
            월드컵을 다시 하면 음식 선호도가 초기화돼요.<br />
            추천 정확도를 높이고 싶을 때 재도전해보세요.
          </p>
          <button
            onClick={() => navigate('/worldcup')}
            style={{
              background: 'transparent',
              border: '1px solid var(--accent)',
              borderRadius: 'var(--radius-pill)', padding: 'var(--sp-3) var(--sp-5)',
              color: 'var(--accent-ink)', fontSize: 'var(--fs-base)', cursor: 'pointer',
              fontWeight: 'var(--fw-medium)', alignSelf: 'flex-start',
              transition: 'var(--transition)',
            }}
          >
            월드컵 재도전
          </button>
        </Section>

        {/* 계정 관리 */}
        <Section title="🗑️ 계정 관리">
          <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', margin: 0, lineHeight: 'var(--lh-base)' }}>
            회원 탈퇴 시 이름, 위치, 신체 정보 등 개인정보는 즉시 삭제돼요.<br />
            식사 기록, 일기, 일정 등은 서비스 개선을 위해 익명으로 보존될 수 있어요.
          </p>
          <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
            <button
              onClick={async () => {
                sessionStorage.removeItem('mukgoorm_profile')
                localStorage.removeItem('mukgoorm_chargen')
                await supabase.auth.signOut()
                navigate('/login')
              }}
              style={{
                background: 'transparent',
                border: '1px solid var(--border-strong)',
                borderRadius: 'var(--radius-pill)', padding: 'var(--sp-3) var(--sp-5)',
                color: 'var(--text-muted)', fontSize: 'var(--fs-base)', cursor: 'pointer',
                transition: 'var(--transition)',
              }}
            >
              로그아웃
            </button>
            <button
              onClick={() => setShowDeleteModal(true)}
              style={{
                background: 'transparent',
                border: '1px solid var(--danger)',
                borderRadius: 'var(--radius-pill)', padding: 'var(--sp-3) var(--sp-5)',
                color: 'var(--danger)', fontSize: 'var(--fs-base)', cursor: 'pointer',
                transition: 'var(--transition)',
              }}
            >
              회원 탈퇴
            </button>
          </div>
        </Section>
      </div>

      {/* 탈퇴 확인 모달 */}
      {showDeleteModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(74, 63, 58, 0.45)',
          backdropFilter: 'blur(2px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }}>
          <div style={{
            background: 'var(--surface)', borderRadius: 'var(--radius-xl)', padding: 32,
            width: 360, display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)',
            boxShadow: 'var(--shadow-lg)',
          }}>
            <h3 style={{ color: 'var(--text-strong)', margin: 0, fontSize: 'var(--fs-lg)' }}>정말 탈퇴할까요?</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', margin: 0, lineHeight: 'var(--lh-base)' }}>
              개인정보(이름, 위치, 신체 정보, 이메일)는 즉시 삭제돼요.<br />
              식사 기록 등 다른 데이터는 익명으로 보존돼요.<br />
              <strong style={{ color: 'var(--danger)' }}>이 작업은 되돌릴 수 없어요.</strong>
            </p>
            <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
              <button
                onClick={() => setShowDeleteModal(false)}
                style={{
                  flex: 1, background: 'var(--surface-2)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)', padding: 'var(--sp-3)',
                  color: 'var(--text)', fontSize: 'var(--fs-base)', cursor: 'pointer',
                  transition: 'var(--transition)',
                }}
              >취소</button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleteLoading}
                style={{
                  flex: 1, background: 'var(--danger)', border: 'none',
                  borderRadius: 'var(--radius-sm)', padding: 'var(--sp-3)',
                  color: 'var(--text-on-accent)', fontSize: 'var(--fs-base)', fontWeight: 'var(--fw-bold)',
                  cursor: deleteLoading ? 'not-allowed' : 'pointer',
                  transition: 'var(--transition)',
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
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)', padding: 'var(--sp-6)',
      display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)',
      boxShadow: 'var(--shadow-sm)',
    }}>
      <h3 style={{ color: 'var(--text-strong)', margin: 0, fontSize: 'var(--fs-base)', fontWeight: 'var(--fw-bold)' }}>{title}</h3>
      {children}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)' }}>{label}</label>
      {children}
    </div>
  )
}

function ToggleBtn({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-sm)', padding: 'var(--sp-2) var(--sp-4)',
      color: active ? 'var(--text-on-accent)' : 'var(--text)', fontSize: 'var(--fs-sm)', cursor: 'pointer',
      background: active ? 'var(--accent)' : 'var(--surface-2)',
      transition: 'var(--transition)',
    }}>{label}</button>
  )
}


const inputStyle: React.CSSProperties = {
  background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
  padding: 'var(--sp-2) var(--sp-4)', color: 'var(--text)', fontSize: 'var(--fs-base)', outline: 'none',
  width: '100%', boxSizing: 'border-box',
}
