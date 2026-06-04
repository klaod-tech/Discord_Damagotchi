# 프론트엔드 다음 개선 사항

## 🔴 버그 수정

### ✅ 1. 회원탈퇴 시 Auth 유저 미삭제 — 구현 완료, 테스트 필요
**현상**: 회원탈퇴 후 동일 계정으로 재로그인 가능. `users` 테이블 row는 삭제되지만 Supabase Auth 유저가 남아 있어 같은 이메일/비밀번호로 재가입 없이 로그인됨.

**해결**: `supabase/functions/delete-user/index.ts` Edge Function 생성 완료.  
`handleDeleteAccount` (Settings.tsx)에서 Edge Function 호출 + `users` 테이블 삭제 + `signOut` 순서로 처리.  
> ⚠️ 실제 탈퇴 후 재로그인 테스트는 아직 미확인.

---

### ✅ 2. evoState 초기값 오류 — 수정 완료
**파일**: [web/src/pages/Home.tsx](../web/src/pages/Home.tsx)

**현상**: 앱 로드 시 캐릭터 진화 상태 체크를 건너뜀. 진화 여부를 확인하기 전에 `'evolved'`로 시작해 조건 분기가 틀어짐.

**수정**: `EvoState`에 `'checking'` 추가, 초기값을 `'checking'`으로 변경. 헤더 텍스트에 `'checking'` 케이스("불러오는 중...") 추가.

---

### ✅ 3. Worldcup.tsx 셔플 편향 — 수정 완료
**파일**: [web/src/pages/Worldcup.tsx](../web/src/pages/Worldcup.tsx)

**현상**: 음식 월드컵 대진 순서가 무작위처럼 보이지만 실제로는 편향 있음.

**수정**: `sort(() => Math.random() - 0.5)` → Fisher-Yates 알고리즘으로 교체.

---

### ✅ 4. email_app_pw 보안 취약점 — 수정 완료
**파일**: [web/src/hooks/useUser.ts](../web/src/hooks/useUser.ts)

**현상**: 이메일 앱 비밀번호가 sessionStorage에 평문으로 저장됨. XSS 공격 시 탈취 가능.

**수정**: `setCachedProfile`에서 `email_app_pw`를 destructuring으로 제외하고 저장.

---

---

## ✅ 이번 세션 완료 (2026-05-26)

| 항목 | 파일 |
|---|---|
| 이메일 카드 5개 표시 — 신규/기존 배지, 펼치기 요약 | `Home.tsx` |
| `EmailItem` 인터페이스 + `CombinedResponse.emails` 필드 | `n8n.ts` |
| 이메일 봇 타임아웃 60초 (`BOT_TIMEOUT`) | `n8n.ts` |
| 음식추천 타임아웃 10초 → 180초 (`recommendFood`) | `n8n.ts` |
| `CLASSIFY_PROMPT` 날씨 규칙 강화 — 직접 질문 시에만 날씨 봇 호출 | `n8n.ts` |
| 로그아웃 버튼 추가 — 계정 관리 섹션 회원탈퇴 옆 | `Settings.tsx` |

---

### ✅ 2. BOT_TIMEOUT — 이메일 타임아웃 적용
**파일**: [web/src/lib/n8n.ts](../web/src/lib/n8n.ts)

**수정**: `BOT_TIMEOUT = { 이메일: 60000 }` — 이메일 봇은 60초, 나머지는 `DEFAULT_TIMEOUT` (15초) 사용.  
(이전에 빈 객체로 정리했으나, 이메일 처리 시간이 길어 다시 도입)
