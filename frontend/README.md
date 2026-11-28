# NexaMind Frontend

The React frontend for NexaMind, a Gemini-powered conversational AI application.

## Technology

- React
- JavaScript (ES modules)
- Vite
- React Router
- Axios
- ESLint

## Requirements

- Node.js 22 or compatible supported version
- npm

## Getting started

Install dependencies:

    npm install

Create your local environment file:

    cp .env.example .env.local

Configure VITE_API_BASE_URL in .env.local to point to the NexaMind backend API.

Start the development server:

    npm run dev

## Available scripts

| Command | Purpose |
|---|---|
| npm run dev | Start development server |
| npm run build | Create production build |
| npm run preview | Preview production build |
| npm run lint | Run ESLint |

## Environment variables

| Variable | Description |
|---|---|
| VITE_API_BASE_URL | Public base URL of the backend API |

Never store API keys, database credentials, or other backend secrets in frontend environment variables.
