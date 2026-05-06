import { supabase } from './supabase'

export async function getUserProfile(userId: string) {
  const { data } = await supabase
    .from('users')
    .select('*')
    .eq('user_id', userId)
    .maybeSingle()
  return data
}

export async function createUserProfile(profile: {
  user_id: string
  tamagotchi_name: string
  city: string
  village: string
  gender: string
  age: number
  height: number
  init_weight: number
  goal_weight: number
  allergies: string[]
  food_preferences: string[]
  wake_time: string
  breakfast_time: string
  lunch_time: string
  dinner_time: string
  snack_time?: string
  email_provider?: string
  email_address?: string
  email_app_pw?: string
}) {
  const { error } = await supabase.from('users').upsert(profile, { onConflict: 'user_id' })
  if (error) throw new Error(error.message + ' | code: ' + error.code)
}

export async function updateUserProfile(userId: string, updates: Record<string, unknown>) {
  const { error } = await supabase.from('users').update(updates).eq('user_id', userId)
  if (error) throw error
}
