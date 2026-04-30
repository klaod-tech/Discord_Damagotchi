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

    async function init() {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (!mounted) return

        const authUser = session?.user ?? null
        setUser(authUser)

        if (authUser) {
          const p = await getUserProfile(authUser.id).catch(() => null)
          if (!mounted) return
          setProfile(p)
        }
      } catch {
        // 세션 조회 실패해도 loading은 해제
      } finally {
        if (mounted) setLoading(false)
      }
    }

    init()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
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
    })

    return () => {
      mounted = false
      subscription.unsubscribe()
    }
  }, [])

  return { user, profile, loading }
}
