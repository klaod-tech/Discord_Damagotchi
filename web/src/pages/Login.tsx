import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    const { error } = isSignUp
      ? await supabase.auth.signUp({ email, password })
      : await supabase.auth.signInWithPassword({ email, password })

    setLoading(false)

    if (error) {
      setError(error.message)
      return
    }

    navigate('/')
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0f0f23',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        background: '#1a1a2e',
        borderRadius: 16,
        padding: 40,
        width: 360,
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 40 }}>🌧️</div>
          <h1 style={{ color: '#fff', margin: '8px 0 4px', fontSize: 22 }}>먹구름</h1>
          <p style={{ color: '#aaa', fontSize: 13, margin: 0 }}>
            {isSignUp ? '계정을 만들어요' : '다시 돌아왔네요'}
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input
            type="email"
            placeholder="이메일"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            style={inputStyle}
          />
          <input
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            style={inputStyle}
          />
          {error && <p style={{ color: '#ff6b6b', fontSize: 13, margin: 0 }}>{error}</p>}
          <button type="submit" disabled={loading} style={buttonStyle}>
            {loading ? '처리 중...' : isSignUp ? '회원가입' : '로그인'}
          </button>
        </form>

        <button
          onClick={() => { setIsSignUp(v => !v); setError('') }}
          style={{ background: 'none', border: 'none', color: '#6c63ff', cursor: 'pointer', fontSize: 13 }}
        >
          {isSignUp ? '이미 계정이 있어요 → 로그인' : '계정이 없어요 → 회원가입'}
        </button>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  background: '#16213e',
  border: '1px solid #2a2a4a',
  borderRadius: 8,
  padding: '12px 16px',
  color: '#fff',
  fontSize: 14,
  outline: 'none',
}

const buttonStyle: React.CSSProperties = {
  background: '#6c63ff',
  border: 'none',
  borderRadius: 8,
  padding: '12px 16px',
  color: '#fff',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
  marginTop: 4,
}
