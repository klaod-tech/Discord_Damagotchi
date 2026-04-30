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
  gender: string
  age: number
  height: number
  goal_weight: number
  wake_time: string
  breakfast_time: string
  lunch_time: string
  dinner_time: string
}) {
  const { error } = await supabase.from('users').upsert(profile, { onConflict: 'user_id' })
  if (error) throw new Error(error.message + ' | code: ' + error.code)
}

export async function updateUserProfile(userId: string, updates: Record<string, unknown>) {
  const { error } = await supabase.from('users').update(updates).eq('user_id', userId)
  if (error) throw error
}
