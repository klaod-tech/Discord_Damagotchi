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
    supabase.auth.getSession().then(async ({ data }) => {
      const authUser = data.session?.user ?? null
      setUser(authUser)
      if (authUser) {
        try {
          const p = await getUserProfile(authUser.id)
          setProfile(p)
        } catch {
          setProfile(null)
        }
      }
      setLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange(async (_event, session) => {
      const authUser = session?.user ?? null
      setUser(authUser)
      if (authUser) {
        const p = await getUserProfile(authUser.id)
        setProfile(p)
      } else {
        setProfile(null)
      }
    })

    return () => listener.subscription.unsubscribe()
  }, [])

  return { user, profile, loading }
}
