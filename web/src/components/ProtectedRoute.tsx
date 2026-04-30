import { Navigate } from 'react-router-dom'
import { useUser } from '../hooks/useUser'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useUser()

  if (loading) return <div style={{ color: '#fff', padding: 32 }}>로딩 중...</div>
  if (!user) return <Navigate to="/login" replace />

  return <>{children}</>
}
