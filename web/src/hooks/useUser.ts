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
        console.log('[useUser] auth event:', event, session?.user?.id)
        if (!mounted) return

        const authUser = session?.user ?? null
        setUser(authUser)

        if (authUser) {
          // 캐시 없을 때만 DB 조회
          const cached = getCachedProfile()
          if (cached && cached.user_id === authUser.id) {
            setProfile(cached)
            clearTimeout(safetyTimer)
            if (mounted) setLoading(false)
            // 백그라운드에서 최신 데이터 갱신
            getUserProfile(authUser.id)
              .then(p => { if (p && mounted) { setProfile(p); setCachedProfile(p) } })
              .catch(() => {})
          } else {
            const p = await getUserProfile(authUser.id).catch(() => null)
            if (!mounted) return
            setProfile(p)
            setCachedProfile(p)
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
