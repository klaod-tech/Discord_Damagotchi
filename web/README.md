# 먹구름 웹앱 (React)

Vite + React + TypeScript 기반 프론트엔드.

## 실행

```bash
npm install
npm run dev
```

## 환경변수

`.env.local` 파일 생성 후 아래 값 설정:

```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_OPENAI_API_KEY=
VITE_N8N_CHAT_WEBHOOK_URL=http://localhost:5678/webhook/ad14deab-8a8b-4a6e-9348-c70980340d3f
```

## 구조

```
src/
├── components/   Layout, Sidebar, ProtectedRoute
├── pages/        Home, Login, Onboarding, Meal, Weight ...
├── lib/          supabase, n8n, openai, db, image
└── hooks/        useUser
```

## 배포

Railway에 n8n + 웹앱 호스팅. 자세한 내용은 루트 `docs/PRODUCTION_ROADMAP.md` 참고.
