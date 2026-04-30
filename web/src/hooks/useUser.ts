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

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T | null> {
  return Promise.race([
    promise,
    new Promise<null>(resolve => setTimeout(() => resolve(null), ms)),
  ])
}

export function useUser() {
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    // 5초 안전망: 어떤 경우에도 로딩 해제
    const safetyTimer = setTimeout(() => {
      if (mounted) setLoading(false)
    }, 5000)

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('[useUser] auth event:', event, session?.user?.id)
        if (!mounted) return

        const authUser = session?.user ?? null
        setUser(authUser)

        if (authUser) {
          // 3초 타임아웃 적용
          const p = await withTimeout(getUserProfile(authUser.id), 10000).catch(() => null)
          if (!mounted) return
          setProfile(p)
        } else {
          setProfile(null)
        }

        clearTimeout(safetyTimer)
        if (mounted) setLoading(false)
      }
    )

    return () => {
      mounted = false
      clearTimeout(safetyTimer)
      subscription.unsubscribe()
    }
  }, [])

  return { user, profile, loading }
}
