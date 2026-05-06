import { useEffect, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { supabase } from '../lib/supabase'

interface WeatherLog {
  id: string
  date: string
  city: string
  temperature: number
  condition: string
  humidity: number | null
  dust_level: string | null
}

export default function Weather() {
  const { user } = useUser()
  const [logs, setLogs] = useState<WeatherLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    supabase
      .from('weather_log')
      .select('*')
      .eq('user_id', user.id)
      .order('date', { ascending: false })
      .then(({ data }) => {
        setLogs(data ?? [])
        setLoading(false)
      })
  }, [user])

  if (loading) return <div style={{ color: '#aaa', padding: 24 }}>로딩 중...</div>

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ color: '#fff', margin: '0 0 24px', fontSize: 20 }}>🌤️ 날씨 기록</h2>
      {logs.length === 0 ? (
        <div style={{ color: '#555', fontSize: 14 }}>기록된 날씨가 없어요.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {logs.map(log => (
            <div key={log.id} style={{
              background: '#1a1a2e', borderRadius: 12, padding: 20,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <div style={{ color: '#aaa', fontSize: 12, marginBottom: 4 }}>
                  {log.date} · {log.city}
                </div>
                <div style={{ color: '#fff', fontSize: 16, fontWeight: 600 }}>{log.condition}</div>
                {(log.humidity || log.dust_level) && (
                  <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
                    {log.humidity && `습도 ${log.humidity}%`}
                    {log.humidity && log.dust_level && ' · '}
                    {log.dust_level && `미세먼지 ${log.dust_level}`}
                  </div>
                )}
              </div>
              <div style={{ color: '#6c63ff', fontSize: 28, fontWeight: 700 }}>{log.temperature}°</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
