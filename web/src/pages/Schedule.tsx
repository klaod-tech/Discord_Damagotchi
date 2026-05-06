import { useEffect, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { supabase } from '../lib/supabase'

interface ScheduleItem {
  id: string
  title: string
  description: string | null
  location: string | null
  date: string
  time: string | null
  is_done: boolean
}

export default function Schedule() {
  const { user } = useUser()
  const [items, setItems] = useState<ScheduleItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    supabase
      .from('schedule')
      .select('*')
      .eq('user_id', user.id)
      .order('date', { ascending: true })
      .then(({ data }) => {
        setItems(data ?? [])
        setLoading(false)
      })
  }, [user])

  async function toggleDone(id: string, current: boolean) {
    setItems(prev => prev.map(i => i.id === id ? { ...i, is_done: !current } : i))
    await supabase.from('schedule').update({ is_done: !current, updated_at: new Date().toISOString() }).eq('id', id)
  }

  const todo = items.filter(i => !i.is_done)
  const done = items.filter(i => i.is_done)

  if (loading) return <div style={{ color: '#aaa', padding: 24 }}>로딩 중...</div>

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ color: '#fff', margin: '0 0 24px', fontSize: 20 }}>📅 일정</h2>
      {items.length === 0 ? (
        <div style={{ color: '#555', fontSize: 14 }}>등록된 일정이 없어요.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[...todo, ...done].map(item => (
            <div key={item.id} style={{
              background: '#1a1a2e', borderRadius: 10, padding: '14px 20px',
              display: 'flex', gap: 14, alignItems: 'flex-start',
              opacity: item.is_done ? 0.5 : 1,
            }}>
              <button
                onClick={() => toggleDone(item.id, item.is_done)}
                style={{
                  marginTop: 2, width: 18, height: 18, borderRadius: 4,
                  border: '2px solid #6c63ff',
                  background: item.is_done ? '#6c63ff' : 'transparent',
                  cursor: 'pointer', flexShrink: 0,
                }}
              />
              <div style={{ flex: 1 }}>
                <div style={{
                  color: '#fff', fontSize: 14, fontWeight: 600,
                  textDecoration: item.is_done ? 'line-through' : 'none',
                }}>
                  {item.title}
                </div>
                <div style={{ color: '#aaa', fontSize: 12, marginTop: 2 }}>
                  {item.date}
                  {item.time && ` · ${item.time}`}
                  {item.location && ` · ${item.location}`}
                </div>
                {item.description && (
                  <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>{item.description}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
