"""QuickPoll FastAPI backend with WebSocket live tally updates."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

import database
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from models import Poll, PollOption, generate_short_id
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

active_connections: dict[str, set[WebSocket]] = {}


async def broadcast_poll_update(poll_id: str, data: dict[str, Any]) -> None:
    """Broadcast updated vote tallies to all connected WebSocket clients."""
    if poll_id in active_connections:
        dead_conns: set[WebSocket] = set()
        msg = json.dumps(data)
        for ws in active_connections[poll_id]:
            try:
                await ws.send_text(msg)
            except Exception:  # noqa: BLE001
                dead_conns.add(ws)
        active_connections[poll_id] -= dead_conns


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    yield


class CreatePollRequest(BaseModel):
    """Poll creation payload."""

    question: str = Field(..., min_length=3, max_length=300)
    options: list[str] = Field(..., min_length=2, max_length=10)
    allow_multiple: bool = False

    @field_validator("question")
    @classmethod
    def check_question_non_blank(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Question must contain at least 3 non-whitespace characters.")
        return cleaned

    @field_validator("options")
    @classmethod
    def check_options_non_blank_and_unique(cls, opts: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in opts:
            item = raw.strip()
            if item and item.lower() not in seen:
                seen.add(item.lower())
                cleaned.append(item)
        if len(cleaned) < 2:
            raise ValueError("Provide at least 2 non-empty distinct poll options.")
        return cleaned


class VoteRequest(BaseModel):
    """Vote cast payload."""

    option_ids: list[int] = Field(..., min_length=1, max_length=10)


def format_poll(poll: Poll) -> dict[str, Any]:
    """Serialize poll and per-option vote percentages."""
    total_votes = sum(o.vote_count for o in poll.options)
    return {
        "id": poll.id,
        "question": poll.question,
        "allow_multiple": poll.allow_multiple,
        "total_votes": total_votes,
        "created_at": poll.created_at.isoformat(),
        "options": [
            {
                "id": o.id,
                "text": o.text,
                "votes": o.vote_count,
                "percentage": round((o.vote_count / total_votes * 100), 1)
                if total_votes > 0
                else 0.0,
            }
            for o in poll.options
        ],
    }


def create_app() -> FastAPI:
    """Build and configure the QuickPoll FastAPI application."""
    application = FastAPI(title="QuickPoll API", version="1.0.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    @application.post("/api/polls", status_code=201)
    async def create_poll(
        req: CreatePollRequest, db: AsyncSession = Depends(database.get_db)
    ) -> dict[str, Any]:
        poll = Poll(
            id=generate_short_id(),
            question=req.question,
            allow_multiple=req.allow_multiple,
        )
        for opt_text in req.options:
            poll.options.append(PollOption(text=opt_text))

        db.add(poll)
        await db.commit()
        await db.refresh(poll, ["options"])
        return format_poll(poll)

    @application.get("/api/polls/{poll_id}")
    async def get_poll(
        poll_id: str, db: AsyncSession = Depends(database.get_db)
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Poll).options(selectinload(Poll.options)).where(Poll.id == poll_id)
        )
        poll = result.scalar_one_or_none()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        return format_poll(poll)

    @application.post("/api/polls/{poll_id}/vote")
    async def vote_poll(
        poll_id: str,
        req: VoteRequest,
        db: AsyncSession = Depends(database.get_db),
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Poll).options(selectinload(Poll.options)).where(Poll.id == poll_id)
        )
        poll = result.scalar_one_or_none()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        unique_ids = list(dict.fromkeys(req.option_ids))
        if not poll.allow_multiple and len(unique_ids) > 1:
            raise HTTPException(
                status_code=400, detail="This poll allows only a single vote."
            )

        option_map = {o.id: o for o in poll.options}
        invalid_ids = [opt_id for opt_id in unique_ids if opt_id not in option_map]
        if invalid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid option ID(s) for poll: {invalid_ids}",
            )

        for opt_id in unique_ids:
            option_map[opt_id].vote_count += 1

        await db.commit()
        await db.refresh(poll, ["options"])

        formatted = format_poll(poll)
        await broadcast_poll_update(poll_id, formatted)
        return formatted

    @application.websocket("/ws/polls/{poll_id}")
    async def poll_websocket(websocket: WebSocket, poll_id: str) -> None:
        await websocket.accept()
        active_connections.setdefault(poll_id, set()).add(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            active_connections.get(poll_id, set()).discard(websocket)

    return application


app = create_app()
