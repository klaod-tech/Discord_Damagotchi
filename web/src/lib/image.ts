export type WeatherType = 'clear' | 'cloudy' | 'rainy' | 'snowy' | 'hot' | 'warm' | 'mask' | 'none'

export function selectCharacterImage(
  weather: WeatherType = 'none',
  hunger: number = 50,
  mood: number = 50,
  hp: number = 100
): string {
  // hp 위험
  if (hp < 20) return '/tired.png'

  // 날씨 우선
  if (weather === 'rainy') return '/rainy.png'
  if (weather === 'snowy') return '/snow.png'
  if (weather === 'hot') return '/hot.png'
  if (weather === 'warm') return '/warm.png'
  if (weather === 'mask') return '/wear mask.png'

  // 식사 직후 (hunger 높음)
  if (hunger > 80) return '/eat.png'

  // 기분 좋음
  if (mood > 70) return '/cheer.png'
  if (mood > 50) return '/smile.png'

  // 배고픔
  if (hunger < 20) return '/upset.png'
  if (hunger < 40) return '/tired.png'

  return '/normal.png'
}
