# quickpoll

Instant live polling and real-time voting web application built with **FastAPI**, **WebSockets**, and **React + Vite**.

## Features

- **Real-Time Vote Broadcasting:** Live bar updates and percentage changes powered by WebSockets.
- **Fast Poll Creation:** Custom questions with 2–8 options, single or multi-choice mode.
- **Shareable Links:** Instant URL generation (`?poll=xyz`) to share polls with audiences or teammates.
- **Sleek Dark Theme:** Clean and responsive UI with smooth CSS transitions.
- **Lightweight Backend:** Async SQLAlchemy 2.0 with SQLite (`aiosqlite`).

## Stack

- **Backend:** FastAPI, SQLite, SQLAlchemy 2.0 (async), WebSockets
- **Frontend:** React 18, Vite, Modern CSS
- **Containerization:** Docker & Docker Compose

## Quick Start

### Docker Compose

```bash
docker compose up --build
```

Access the frontend at `http://localhost:3000` (API runs on `http://localhost:8000`).

### Manual Setup

```bash
# 1. Start backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 2. Start frontend
cd ../frontend
npm install
npm run dev
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/polls` | Create new poll |
| GET | `/api/polls/:id` | Get poll metadata and options |
| POST | `/api/polls/:id/vote` | Cast vote for option(s) |
| WS | `/ws/polls/:id` | WebSocket stream for live vote counts |
