import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { getUserProfile } from '../lib/db'
import type { User } from '@supabase/supabase-js'

export interface UserProfile {
  user_id: string
  tamagotchi_name: string
  city: string
  address?: string
  gender?: string
  age?: number
  height?: number
  goal_weight?: number
  daily_cal_target?: number
  wake_time?: string
  breakfast_time?: string
  lunch_time?: string
  dinner_time?: string
  streak?: number
  max_streak?: number
  badges?: string
}

export function useUser() {
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    // getSession() 대신 onAuthStateChange만 사용
    // INITIAL_SESSION 이벤트가 페이지 로드 시 저장된 세션을 즉시 전달함
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (!mounted) return

        const authUser = session?.user ?? null
        setUser(authUser)

        if (authUser) {
          const p = await getUserProfile(authUser.id).catch(() => null)
          if (!mounted) return
          setProfile(p)
        } else {
          setProfile(null)
        }

        if (mounted) setLoading(false)
      }
    )

    return () => {
      mounted = false
      subscription.unsubscribe()
    }
  }, [])

  return { user, profile, loading }
}
