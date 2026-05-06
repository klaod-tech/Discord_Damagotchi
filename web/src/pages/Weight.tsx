import { useEffect, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { supabase } from '../lib/supabase'

interface WeightLog {
  id: string
  date: string
  weight: number
  bmi: number | null
  note: string | null
}

export default function Weight() {
  const { user, profile } = useUser()
  const [logs, setLogs] = useState<WeightLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    supabase
      .from('weight_log')
      .select('*')
      .eq('user_id', user.id)
      .order('date', { ascending: false })
      .then(({ data }) => {
        setLogs(data ?? [])
        setLoading(false)
      })
  }, [user])

  const latest = logs[0]
  const goal = profile?.goal_weight

  if (loading) return <div style={{ color: '#aaa', padding: 24 }}>로딩 중...</div>

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ color: '#fff', margin: '0 0 24px', fontSize: 20 }}>⚖️ 체중 관리</h2>

      {latest && (
        <div style={{ background: '#1a1a2e', borderRadius: 12, padding: 20, marginBottom: 16, display: 'flex', gap: 32 }}>
          <div>
            <div style={{ color: '#aaa', fontSize: 12, marginBottom: 4 }}>현재 체중</div>
            <div style={{ color: '#fff', fontSize: 24, fontWeight: 700 }}>{latest.weight} kg</div>
          </div>
          {goal && (
            <div>
              <div style={{ color: '#aaa', fontSize: 12, marginBottom: 4 }}>목표까지</div>
              <div style={{ color: '#6c63ff', fontSize: 24, fontWeight: 700 }}>
                {latest.weight > goal
                  ? `-${(latest.weight - goal).toFixed(1)}`
                  : `+${(goal - latest.weight).toFixed(1)}`} kg
              </div>
            </div>
          )}
          {latest.bmi && (
            <div>
              <div style={{ color: '#aaa', fontSize: 12, marginBottom: 4 }}>BMI</div>
              <div style={{ color: '#fff', fontSize: 24, fontWeight: 700 }}>{latest.bmi}</div>
            </div>
          )}
        </div>
      )}

      {logs.length === 0 ? (
        <div style={{ color: '#555', fontSize: 14 }}>기록된 체중이 없어요.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {logs.map(log => (
            <div key={log.id} style={{
              background: '#1a1a2e', borderRadius: 10, padding: '14px 20px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <span style={{ color: '#aaa', fontSize: 13 }}>{log.date}</span>
                {log.note && <span style={{ color: '#555', fontSize: 12, marginLeft: 10 }}>{log.note}</span>}
              </div>
              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                {log.bmi && <span style={{ color: '#888', fontSize: 13 }}>BMI {log.bmi}</span>}
                <span style={{ color: '#fff', fontSize: 15, fontWeight: 600 }}>{log.weight} kg</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
