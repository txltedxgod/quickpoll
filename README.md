# quickpoll

> Instant live polling and real-time voting web app with live bar updates and WebSockets.

[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![WebSocket](https://img.shields.io/badge/WebSocket-Realtime-blueviolet?style=flat-square)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite)](https://vitejs.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

`#polling-app` `#voting-system` `#websockets` `#react` `#fastapi` `#realtime` `#developer-tools`

---

## Features

- **Live Real-Time Broadcasting:** Instant percentage & progress bar animations via WebSockets.
- **Fast Poll Creation:** Single-choice or multi-choice polls with 2–8 customizable options.
- **Instant Shareable Links:** Generate direct voting links (`?poll=xyz`) for quick sharing.
- **Sleek Dark Theme:** Modern responsive UI styled with GitHub-inspired dark color tokens.
- **Async Backend:** FastAPI with SQLAlchemy 2.0 and `aiosqlite`.

## Quick Start

### With Docker Compose

```bash
docker compose up --build
```

Access the frontend at `http://localhost:3000` (FastAPI backend running on `http://localhost:8000`).

### Manual Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd ../frontend
npm install
npm run dev
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/polls` | Create a new poll |
| `GET` | `/api/polls/:id` | Get poll questions, options, and vote tallies |
| `POST` | `/api/polls/:id/vote` | Cast vote for option(s) and broadcast update |
| `WS` | `/ws/polls/:id` | WebSocket stream for live vote counts |
