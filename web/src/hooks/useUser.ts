import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import { getUserProfile } from '../lib/db'
import type { User } from '@supabase/supabase-js'

export interface UserProfile {
  user_id: string
  tamagotchi_name: string
  city: string
  village?: string
  gender?: string
  age?: number
  height?: number
  init_weight?: number
  goal_weight?: number
  daily_cal_target?: number
  wake_time?: string
  breakfast_time?: string
  lunch_time?: string
  dinner_time?: string
  snack_time?: string
  allergies?: string[]
  food_preferences?: string[]
  email_provider?: string
  email_address?: string
  email_app_pw?: string
  streak?: number
  max_streak?: number
  badges?: string
}

const PROFILE_CACHE_KEY = 'mukgoorm_profile'

function getCachedProfile(): UserProfile | null {
  try {
    const raw = sessionStorage.getItem(PROFILE_CACHE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function setCachedProfile(profile: UserProfile | null) {
  try {
    if (profile) sessionStorage.setItem(PROFILE_CACHE_KEY, JSON.stringify(profile))
    else sessionStorage.removeItem(PROFILE_CACHE_KEY)
  } catch {}
}

export function useUser() {
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(getCachedProfile)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true

    const safetyTimer = setTimeout(() => {
      if (mounted) setLoading(false)
    }, 10000)

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (!mounted) return

        const authUser = session?.user ?? null
        setUser(authUser)

        if (authUser) {
          const cached = getCachedProfile()
          if (cached && cached.user_id === authUser.id) {
            setProfile(cached)
            clearTimeout(safetyTimer)
            if (mounted) setLoading(false)
            getUserProfile(authUser.id)
              .then(p => { if (p && mounted) { setProfile(p as UserProfile); setCachedProfile(p as UserProfile) } })
              .catch(() => {})
          } else {
            const p = await getUserProfile(authUser.id).catch(() => null)
            if (!mounted) return
            setProfile(p as UserProfile | null)
            setCachedProfile(p as UserProfile | null)
            clearTimeout(safetyTimer)
            if (mounted) setLoading(false)
          }
        } else {
          setProfile(null)
          setCachedProfile(null)
          clearTimeout(safetyTimer)
          if (mounted) setLoading(false)
        }
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
