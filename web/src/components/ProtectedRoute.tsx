import { Navigate, Outlet } from 'react-router-dom'
import { useUser } from '../hooks/useUser'

export default function ProtectedRoute() {
  const { user, loading } = useUser()

  if (loading) return <div style={{ color: '#fff', padding: 32 }}>로딩 중...</div>
  if (!user) return <Navigate to="/login" replace />

  return <Outlet />
}
