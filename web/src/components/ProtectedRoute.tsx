import { Navigate, Outlet } from 'react-router-dom'
import { useUser } from '../hooks/useUser'

export default function ProtectedRoute() {
  const { user, profile, loading } = useUser()

  if (loading) return <div style={{ color: '#fff', padding: 32, minHeight: '100vh', background: '#0f0f23' }}>로딩 중...</div>
  if (!user) return <Navigate to="/login" replace />
  if (!profile) return <Navigate to="/onboarding" replace />

  return <Outlet />
}
