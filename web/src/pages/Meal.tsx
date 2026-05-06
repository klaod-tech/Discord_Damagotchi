import { useEffect, useState } from 'react'
import { useUser } from '../hooks/useUser'
import { supabase } from '../lib/supabase'

interface MealLog {
  id: string
  date: string
  meal_type: string
  food_name: string
  calories: number
}

const MEAL_LABEL: Record<string, string> = {
  breakfast: '아침',
  lunch: '점심',
  dinner: '저녁',
  snack: '간식',
  unknown: '기타',
}

export default function Meal() {
  const { user } = useUser()
  const [logs, setLogs] = useState<MealLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    supabase
      .from('meal_log')
      .select('*')
      .eq('user_id', user.id)
      .order('date', { ascending: false })
      .order('created_at', { ascending: false })
      .then(({ data }) => {
        setLogs(data ?? [])
        setLoading(false)
      })
  }, [user])

  const grouped = logs.reduce<Record<string, MealLog[]>>((acc, log) => {
    if (!acc[log.date]) acc[log.date] = []
    acc[log.date].push(log)
    return acc
  }, {})

  if (loading) return <div style={{ color: '#aaa', padding: 24 }}>로딩 중...</div>

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ color: '#fff', margin: '0 0 24px', fontSize: 20 }}>🍽️ 식사 기록</h2>
      {Object.keys(grouped).length === 0 ? (
        <div style={{ color: '#555', fontSize: 14 }}>기록된 식사가 없어요.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {Object.entries(grouped).map(([date, items]) => {
            const total = items.reduce((s, i) => s + (i.calories ?? 0), 0)
            return (
              <div key={date} style={{ background: '#1a1a2e', borderRadius: 12, padding: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                  <span style={{ color: '#fff', fontWeight: 600, fontSize: 15 }}>{date}</span>
                  <span style={{ color: '#6c63ff', fontSize: 13 }}>총 {total} kcal</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {items.map(item => (
                    <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <span style={{ color: '#aaa', fontSize: 12, marginRight: 8 }}>
                          {MEAL_LABEL[item.meal_type] ?? item.meal_type}
                        </span>
                        <span style={{ color: '#fff', fontSize: 14 }}>{item.food_name}</span>
                      </div>
                      <span style={{ color: '#888', fontSize: 13 }}>{item.calories} kcal</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
