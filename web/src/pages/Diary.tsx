import { useEffect, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { supabase } from '../lib/supabase'

interface DiaryEntry {
  id: string
  date: string
  content: string
  summary: string | null
}

export default function Diary() {
  const { user } = useUser()
  const [entries, setEntries] = useState<DiaryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    supabase
      .from('diary')
      .select('*')
      .eq('user_id', user.id)
      .order('date', { ascending: false })
      .then(({ data }) => {
        setEntries(data ?? [])
        setLoading(false)
      })
  }, [user])

  if (loading) return <div style={{ color: '#aaa', padding: 24 }}>로딩 중...</div>

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ color: '#fff', margin: '0 0 24px', fontSize: 20 }}>📔 일기</h2>
      {entries.length === 0 ? (
        <div style={{ color: '#555', fontSize: 14 }}>작성된 일기가 없어요.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {entries.map(entry => (
            <div
              key={entry.id}
              onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
              style={{ background: '#1a1a2e', borderRadius: 12, padding: 20, cursor: 'pointer' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#fff', fontWeight: 600, fontSize: 15 }}>{entry.date}</span>
                <span style={{ color: '#555', fontSize: 12 }}>{expanded === entry.id ? '▲' : '▼'}</span>
              </div>
              {entry.summary && (
                <div style={{ color: '#aaa', fontSize: 13, marginTop: 6 }}>{entry.summary}</div>
              )}
              {expanded === entry.id && (
                <div style={{
                  color: '#ccc', fontSize: 14, marginTop: 12, lineHeight: 1.7,
                  whiteSpace: 'pre-wrap', borderTop: '1px solid #2a2a4a', paddingTop: 12,
                }}>
                  {entry.content}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
