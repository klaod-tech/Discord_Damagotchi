import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUser } from '../hooks/useUser'
import { supabase } from '../lib/supabase'
import { sendWorldcupResult, type WorldcupRound } from '../lib/n8n'
import { getCharacterGen, resumeOrStartGeneration, type CharacterGen } from '../lib/characterGen'

interface Food {
  name: string
  category: string
  image: string
}

type RoundResult = WorldcupRound

type TournamentSize = 16 | 32 | 64

const FOOD_POOL: Food[] = [
  // ── 한식 16개
  { name: '삼겹살',     category: '한식',   image: '/foods/samgyeopsal.png' },
  { name: '김치찌개',   category: '한식',   image: '/foods/kimchijjigae.png' },
  { name: '비빔밥',     category: '한식',   image: '/foods/bibimbap.png' },
  { name: '순대국밥',   category: '한식',   image: '/foods/sundaegukbap.png' },
  { name: '족발',      category: '한식',   image: '/foods/jokbal.png' },
  { name: '갈비찜',     category: '한식',   image: '/foods/galbijjim.png' },
  { name: '된장찌개',   category: '한식',   image: '/foods/doenjangjjigae.png' },
  { name: '불고기',     category: '한식',   image: '/foods/bulgogi.png' },
  { name: '닭갈비',     category: '한식',   image: '/foods/dakgalbi.png' },
  { name: '삼계탕',     category: '한식',   image: '/foods/samgyetang.png' },
  { name: '해장국',     category: '한식',   image: '/foods/haejanguk.png' },
  { name: '냉면',      category: '한식',   image: '/foods/naengmyeon.png' },
  { name: '칼국수',     category: '한식',   image: '/foods/kalguksu.png' },
  { name: '보쌈',      category: '한식',   image: '/foods/bossam.png' },
  { name: '잡채',      category: '한식',   image: '/foods/japchae.png' },
  { name: '갈비탕',     category: '한식',   image: '/foods/galbitang.png' },
  // ── 중식 8개
  { name: '짜장면',     category: '중식',   image: '/foods/jajangmyeon.png' },
  { name: '짬뽕',      category: '중식',   image: '/foods/jjambbong.png' },
  { name: '탕수육',     category: '중식',   image: '/foods/tangsuyuk.png' },
  { name: '마라탕',     category: '중식',   image: '/foods/maratang.png' },
  { name: '마파두부',   category: '중식',   image: '/foods/mapadubu.png' },
  { name: '딤섬',      category: '중식',   image: '/foods/dimsum.png' },
  { name: '깐풍기',     category: '중식',   image: '/foods/kkampunggi.png' },
  { name: '양장피',     category: '중식',   image: '/foods/yangjangpi.png' },
  // ── 양식 8개
  { name: '피자',      category: '양식',   image: '/foods/pizza.png' },
  { name: '스테이크',   category: '양식',   image: '/foods/steak.png' },
  { name: '파스타',     category: '양식',   image: '/foods/pasta.png' },
  { name: '햄버거',     category: '양식',   image: '/foods/hamburger.png' },
  { name: '리조또',     category: '양식',   image: '/foods/risotto.png' },
  { name: '바비큐립',   category: '양식',   image: '/foods/bbqrib.png' },
  { name: '샐러드',     category: '양식',   image: '/foods/salad.png' },
  { name: '클럽샌드위치', category: '양식',  image: '/foods/clubsandwich.png' },
  // ── 분식 8개
  { name: '치킨',      category: '분식',   image: '/foods/chicken.png' },
  { name: '떡볶이',     category: '분식',   image: '/foods/tteokbokki.png' },
  { name: '순대',      category: '분식',   image: '/foods/sundae.png' },
  { name: '어묵',      category: '분식',   image: '/foods/eomuk.png' },
  { name: '라면',      category: '분식',   image: '/foods/ramyeon.png' },
  { name: '김밥',      category: '분식',   image: '/foods/gimbap.png' },
  { name: '핫도그',     category: '분식',   image: '/foods/hotdog.png' },
  { name: '붕어빵',     category: '분식',   image: '/foods/bungeoppang.png' },
  // ── 일식 8개
  { name: '초밥',      category: '일식',   image: '/foods/chobap.png' },
  { name: '라멘',      category: '일식',   image: '/foods/ramen.png' },
  { name: '우동',      category: '일식',   image: '/foods/udong.png' },
  { name: '돈까스',     category: '일식',   image: '/foods/donkkaseu.png' },
  { name: '타코야키',   category: '일식',   image: '/foods/takoyaki.png' },
  { name: '텐동',      category: '일식',   image: '/foods/tendon.png' },
  { name: '야키토리',   category: '일식',   image: '/foods/yakitori.png' },
  { name: '가츠동',     category: '일식',   image: '/foods/katsudon.png' },
  // ── 디저트 8개
  { name: '아이스크림',  category: '디저트', image: '/foods/icecream.png' },
  { name: '케이크',     category: '디저트', image: '/foods/cake.png' },
  { name: '마카롱',     category: '디저트', image: '/foods/macaron.png' },
  { name: '와플',      category: '디저트', image: '/foods/waffle.png' },
  { name: '빙수',      category: '디저트', image: '/foods/bingsu.png' },
  { name: '타르트',     category: '디저트', image: '/foods/tart.png' },
  { name: '크레이프',   category: '디저트', image: '/foods/crepe.png' },
  { name: '도넛',      category: '디저트', image: '/foods/donut.png' },
  // ── 기타 8개
  { name: '쌀국수',     category: '기타',   image: '/foods/pho.png' },
  { name: '팟타이',     category: '기타',   image: '/foods/padthai.png' },
  { name: '인도카레',   category: '기타',   image: '/foods/indiancurry.png' },
  { name: '타코',      category: '기타',   image: '/foods/taco.png' },
  { name: '케밥',      category: '기타',   image: '/foods/kebab.png' },
  { name: '훠궈',      category: '기타',   image: '/foods/huoguo.png' },
  { name: '곱창',      category: '기타',   image: '/foods/gobchang.png' },
  { name: '감바스',     category: '기타',   image: '/foods/gambas.png' },
]

const ROUND_LABELS: Record<TournamentSize, Record<number, string>> = {
  64: { 1: '64강', 2: '32강', 3: '16강', 4: '8강', 5: '4강', 6: '결승' },
  32: { 1: '32강', 2: '16강', 3: '8강', 4: '4강', 5: '결승' },
  16: { 1: '16강', 2: '8강', 3: '4강', 4: '결승' },
}

const TOTAL_MATCHES: Record<TournamentSize, number> = { 64: 63, 32: 31, 16: 15 }

// 카테고리별 비율 유지하며 N개 선택 (한식 25%, 나머지 각 12.5%)
function buildFoodPool(size: TournamentSize): Food[] {
  if (size === 64) return shuffle(FOOD_POOL)

  const groups: Record<string, Food[]> = {}
  FOOD_POOL.forEach(f => {
    if (!groups[f.category]) groups[f.category] = []
    groups[f.category].push(f)
  })

  const ratio = size / FOOD_POOL.length
  const result: Food[] = []
  Object.values(groups).forEach(foods => {
    const count = Math.round(foods.length * ratio)
    result.push(...shuffle(foods).slice(0, count))
  })
  return shuffle(result)
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function makePairs(foods: Food[]): Food[][] {
  const pairs: Food[][] = []
  for (let i = 0; i < foods.length; i += 2) pairs.push([foods[i], foods[i + 1]])
  return pairs
}

const SIZE_OPTIONS: { size: TournamentSize; label: string; desc: string; time: string }[] = [
  { size: 16, label: '16강', desc: '15번 선택', time: '약 3분' },
  { size: 32, label: '32강', desc: '31번 선택', time: '약 7분' },
  { size: 64, label: '64강', desc: '63번 선택', time: '약 15분' },
]

export default function Worldcup() {
  const navigate = useNavigate()
  const { profile } = useUser()

  const [checking, setChecking] = useState(true)
  const [alreadyCompleted, setAlreadyCompleted] = useState(false)
  const [previousChampion, setPreviousChampion] = useState<string | null>(null)
  const [previousTopCategory, setPreviousTopCategory] = useState<string>('기타')

  const [tournamentSize, setTournamentSize] = useState<TournamentSize | null>(null)
  const [pairs, setPairs] = useState<Food[][]>([])
  const [pairIndex, setPairIndex] = useState(0)
  const [roundNumber, setRoundNumber] = useState(1)
  const [roundResults, setRoundResults] = useState<RoundResult[]>([])
  const [pendingWinners, setPendingWinners] = useState<Food[]>([])
  const [champion, setChampion] = useState<Food | null>(null)
  const [topCategories, setTopCategories] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [charGen, setCharGen] = useState<CharacterGen | null>(null)

  useEffect(() => {
    if (!profile) return
    async function checkCompleted() {
      const { data } = await supabase
        .from('worldcup_sessions')
        .select('champion')
        .eq('user_id', profile!.user_id)
        .eq('completed', true)
        .limit(1)
      if (data && data.length > 0) {
        setAlreadyCompleted(true)
        setPreviousChampion(data[0].champion)
        const { data: logits } = await supabase
          .from('user_preference_logits')
          .select('category, logit')
          .eq('user_id', profile!.user_id)
        if (logits && logits.length > 0) {
          const top = logits.sort((a, b) => b.logit - a.logit)[0].category
          setPreviousTopCategory(top)
        }
      }
      setChecking(false)
    }
    checkCompleted()
  }, [profile])

  function startTournament(size: TournamentSize) {
    const pool = buildFoodPool(size)
    setTournamentSize(size)
    setPairs(makePairs(pool))
    setPairIndex(0)
    setRoundNumber(1)
    setRoundResults([])
    setPendingWinners([])
  }

  async function handlePick(winner: Food, loser: Food) {
    const result: RoundResult = {
      round: roundNumber,
      winner: winner.name,
      loser: loser.name,
      winner_category: winner.category,
      loser_category: loser.category,
    }
    const newResults = [...roundResults, result]
    const newWinners = [...pendingWinners, winner]
    const isLastPair = pairIndex === pairs.length - 1

    if (isLastPair) {
      if (newWinners.length === 1) {
        setChampion(newWinners[0])
        setRoundResults(newResults)
        await handleComplete(newResults, newWinners[0])
      } else {
        setPairs(makePairs(newWinners))
        setPairIndex(0)
        setRoundNumber(r => r + 1)
        setRoundResults(newResults)
        setPendingWinners([])
      }
    } else {
      setPairIndex(p => p + 1)
      setRoundResults(newResults)
      setPendingWinners(newWinners)
    }
  }

  async function handleComplete(results: RoundResult[], champ: Food) {
    if (!profile) { navigate('/'); return }
    setSubmitting(true)
    try {
      const data = await sendWorldcupResult({
        user_id: profile.user_id,
        champion: champ.name,
        rounds: results,
      })
      setTopCategories(data.top_categories ?? [])
      resumeOrStartGeneration(profile.user_id, data.top_categories?.[0] ?? '기타')
      const gen = await getCharacterGen(profile.user_id)
      setCharGen(gen)
    } catch (e) {
      console.error('[Worldcup] 저장 오류:', e)
      const msg = e instanceof Error ? e.message : ''
      if (msg.includes('timeout')) {
        // n8n이 저장은 완료했을 가능성이 높으므로 그냥 진행
        resumeOrStartGeneration(profile.user_id, '기타')
      } else {
        alert(msg || '점수 저장 중 오류가 발생했어요. 다시 시도해주세요.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  // ── 로딩 화면 ────────────────────────────────────────────────
  if (checking) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-faint)', fontSize: 'var(--fs-base)' }}>확인 중...</div>
      </div>
    )
  }

  // ── 이미 완료 화면 ──────────────────────────────────────────
  if (alreadyCompleted) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--sp-6)' }}>
          <div style={{ fontSize: 48 }}>🏆</div>
          <div>
            <div style={{ color: 'var(--accent-ink)', fontSize: 'var(--fs-sm)', marginBottom: 8, letterSpacing: 1 }}>이미 완료한 월드컵</div>
            <div style={{ color: 'var(--text-strong)', fontSize: 'var(--fs-xl)', fontWeight: 'var(--fw-bold)' }}>
              {previousChampion ? `${previousChampion}이(가) 우승했어요!` : '월드컵을 완료했어요'}
            </div>
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', marginTop: 10, lineHeight: 'var(--lh-base)' }}>
              월드컵은 한 번만 참여할 수 있어요.<br />
              이후 취향은 음식 추천과 피드백으로 쌓여요 🌧️
            </div>
          </div>
          <button
            onClick={() => {
              resumeOrStartGeneration(profile!.user_id, previousTopCategory)
              navigate('/')
            }}
            style={{
              background: 'var(--accent)', border: 'none', borderRadius: 'var(--radius-pill)',
              padding: 'var(--sp-4) var(--sp-10)', color: 'var(--text-on-accent)',
              fontSize: 'var(--fs-md)', fontWeight: 'var(--fw-bold)', cursor: 'pointer',
              boxShadow: 'var(--shadow-accent)', transition: 'var(--transition)',
            }}
          >
            먹구름 만나러 가기 →
          </button>
        </div>
      </div>
    )
  }

  // ── 강 선택 화면 ─────────────────────────────────────────────
  if (!tournamentSize) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ textAlign: 'center', marginBottom: 'var(--sp-10)' }}>
          <div style={{ color: 'var(--accent-ink)', fontSize: 'var(--fs-sm)', marginBottom: 10, letterSpacing: 1 }}>음식 이상형 월드컵</div>
          <div style={{ color: 'var(--text-strong)', fontSize: 'var(--fs-2xl)', fontWeight: 'var(--fw-bold)' }}>몇 강으로 할까요?</div>
          <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', marginTop: 8 }}>
            한 번만 참여할 수 있어요. 신중하게 골라봐요!
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)', width: '100%', maxWidth: 340 }}>
          {SIZE_OPTIONS.map(({ size, label, time }) => (
            <button
              key={size}
              onClick={() => startTournament(size)}
              style={{
                background: 'var(--surface)', border: '2px solid var(--border)',
                borderRadius: 'var(--radius-lg)', padding: 'var(--sp-5) var(--sp-6)',
                cursor: 'pointer', textAlign: 'left',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                boxShadow: 'var(--shadow-sm)', transition: 'var(--transition)',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = 'var(--shadow-accent)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'var(--shadow-sm)' }}
            >
              <div style={{ color: 'var(--text-strong)', fontSize: 'var(--fs-lg)', fontWeight: 'var(--fw-bold)' }}>{label}</div>
              <div style={{ color: 'var(--accent-ink)', fontSize: 'var(--fs-sm)' }}>{time}</div>
            </button>
          ))}
        </div>
      </div>
    )
  }

  const totalMatches = TOTAL_MATCHES[tournamentSize]
  const roundLabel = ROUND_LABELS[tournamentSize]
  const progress = roundResults.length / totalMatches
  const currentPair = pairs[pairIndex]

  // ── 결과 화면 ────────────────────────────────────────────────
  if (champion) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--sp-8)' }}>
          <img src={champion.image} alt={champion.name} style={{ width: 160, height: 160, objectFit: 'cover', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-accent)' }} />
          <div>
            <div style={{ color: 'var(--accent-ink)', fontSize: 'var(--fs-sm)', marginBottom: 8, letterSpacing: 1 }}>🏆 최종 우승</div>
            <div style={{ color: 'var(--text-strong)', fontSize: 'var(--fs-2xl)', fontWeight: 'var(--fw-bold)' }}>{champion.name}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', marginTop: 6 }}>{champion.category}</div>
          </div>

          {topCategories.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
              <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-sm)' }}>선호 카테고리 TOP 3</div>
              <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                {topCategories.map((cat, i) => (
                  <span key={cat} style={{
                    padding: 'var(--sp-1) var(--sp-4)', borderRadius: 'var(--radius-pill)', fontSize: 'var(--fs-sm)',
                    background: i === 0 ? 'var(--accent)' : 'var(--surface-2)',
                    color: i === 0 ? 'var(--text-on-accent)' : 'var(--text)',
                    fontWeight: i === 0 ? 'var(--fw-bold)' : 'var(--fw-regular)',
                    border: `1px solid ${i === 0 ? 'var(--accent)' : 'var(--border)'}`,
                  }}>
                    {i === 0 ? '👑 ' : ''}{cat}
                  </span>
                ))}
              </div>
            </div>
          )}

          {charGen?.status === 'done' && charGen.normal_url ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--sp-3)' }}>
              <img
                src={charGen.normal_url}
                alt="내 캐릭터"
                style={{ width: 160, height: 160, objectFit: 'cover', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-accent)' }}
              />
              <div style={{ color: 'var(--accent-ink)', fontSize: 'var(--fs-sm)', fontWeight: 'var(--fw-medium)' }}>
                나만의 AI 캐릭터가 완성됐어요! 🎉
              </div>
            </div>
          ) : (
            <div style={{
              color: 'var(--text-muted)', fontSize: 'var(--fs-sm)', maxWidth: 280,
              lineHeight: 'var(--lh-base)', background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', padding: 'var(--sp-4) var(--sp-5)',
              boxShadow: 'var(--shadow-sm)',
            }}>
              이 결과로 나만의 AI 캐릭터가 만들어지고 있어요 🌧️<br />
              하루 뒤 큐브가 진화할 거예요!
            </div>
          )}

          <button
            onClick={() => navigate('/')}
            disabled={submitting}
            style={{
              background: 'var(--accent)', border: 'none', borderRadius: 'var(--radius-pill)',
              padding: 'var(--sp-4) var(--sp-10)', color: 'var(--text-on-accent)',
              fontSize: 'var(--fs-md)', fontWeight: 'var(--fw-bold)', cursor: 'pointer',
              opacity: submitting ? 0.6 : 1,
              boxShadow: 'var(--shadow-accent)', transition: 'var(--transition)',
            }}
          >
            {submitting ? '저장 중...' : '먹구름 만나러 가기 →'}
          </button>
        </div>
      </div>
    )
  }

  // ── 대결 화면 ────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      {/* 헤더 */}
      <div style={{ width: '100%', maxWidth: 500, marginBottom: 'var(--sp-10)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <div style={{ color: 'var(--text-strong)', fontWeight: 'var(--fw-bold)', fontSize: 'var(--fs-md)' }}>
            음식 이상형 월드컵
            <span style={{ color: 'var(--accent-ink)', marginLeft: 8, fontSize: 'var(--fs-base)' }}>
              {roundLabel[roundNumber]}
            </span>
          </div>
          <div style={{ color: 'var(--text-faint)', fontSize: 'var(--fs-sm)' }}>
            {roundResults.length} / {totalMatches}
          </div>
        </div>
        <div style={{ width: '100%', height: 6, background: 'var(--border)', borderRadius: 'var(--radius-pill)' }}>
          <div style={{
            width: `${progress * 100}%`, height: '100%',
            background: 'var(--accent)',
            borderRadius: 'var(--radius-pill)', transition: 'width 0.35s ease',
          }} />
        </div>
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-xs)', marginTop: 8, textAlign: 'center' }}>
          먹고 싶은 음식을 골라줘!
        </div>
      </div>

      {/* 대결 카드 */}
      <div style={{ width: '100%', maxWidth: 500, display: 'flex', alignItems: 'center', gap: 'var(--sp-4)' }}>
        <FoodCard food={currentPair[0]} onPick={() => handlePick(currentPair[0], currentPair[1])} />
        <div style={{
          color: 'var(--accent)', fontWeight: 800, fontSize: 22,
          flexShrink: 0,
        }}>VS</div>
        <FoodCard food={currentPair[1]} onPick={() => handlePick(currentPair[1], currentPair[0])} />
      </div>
    </div>
  )
}

function FoodCard({ food, onPick }: { food: Food; onPick: () => void }) {
  const [pressed, setPressed] = useState(false)

  return (
    <button
      onClick={onPick}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      style={{
        flex: 1,
        background: pressed ? 'var(--accent-soft)' : 'var(--surface)',
        border: `2px solid ${pressed ? 'var(--accent)' : 'var(--border)'}`,
        borderRadius: 'var(--radius-xl)', padding: '36px 12px',
        cursor: 'pointer',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--sp-4)',
        transition: 'all 0.12s',
        transform: pressed ? 'scale(0.97)' : 'scale(1)',
        boxShadow: pressed ? 'var(--shadow-accent)' : 'var(--shadow-sm)',
      }}
    >
      <img src={food.image} alt={food.name} style={{ width: 120, height: 120, objectFit: 'cover', borderRadius: 'var(--radius-md)' }} />
      <div style={{ color: 'var(--text-strong)', fontSize: 17, fontWeight: 'var(--fw-bold)' }}>{food.name}</div>
      <div style={{
        fontSize: 'var(--fs-xs)', padding: '3px var(--sp-3)', borderRadius: 'var(--radius-pill)',
        background: 'var(--accent-soft)', color: 'var(--accent-ink)',
      }}>{food.category}</div>
    </button>
  )
}
