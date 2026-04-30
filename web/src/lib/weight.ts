import { supabase } from './supabase'

export async function recordWeight(userId: string, weight: number) {
  const { error } = await supabase.from('weight_log').insert({
    user_id: userId,
    weight,
  })
  if (error) throw error
}

export async function getLatestWeight(userId: string): Promise<number | null> {
  const { data } = await supabase
    .from('weight_log')
    .select('weight')
    .eq('user_id', userId)
    .order('recorded_at', { ascending: false })
    .limit(1)
    .maybeSingle()
  return data?.weight ?? null
}

export async function getWeightHistory(userId: string, days = 14) {
  const since = new Date()
  since.setDate(since.getDate() - days)
  const { data } = await supabase
    .from('weight_log')
    .select('weight, recorded_at')
    .eq('user_id', userId)
    .gte('recorded_at', since.toISOString())
    .order('recorded_at', { ascending: true })
  return data ?? []
}
