This is a Next.js frontend with:
- ScaleKit auth (`sign up`, `log in`, `log out`)
- FastAPI counter integration

## Getting Started

## Environment

Copy `.env.example` to `.env.local` and set:

```bash
SCALEKIT_ENVIRONMENT_URL=
SCALEKIT_CLIENT_ID=
SCALEKIT_CLIENT_SECRET=
SCALEKIT_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Getting Started

Run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000).

Auth endpoints:
- `/api/auth/signup`
- `/api/auth/login`
- `/api/auth/callback`
- `/api/auth/logout`
- `/api/auth/me`
