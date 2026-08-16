from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import init_db, get_db
from models import Poll, PollOption, generate_short_id
from pydantic import BaseModel, Field
from typing import List, Dict, Set
from contextlib import asynccontextmanager
import json

active_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast_poll_update(poll_id: str, data: dict):
    if poll_id in active_connections:
        dead_conns = set()
        msg = json.dumps(data)
        for ws in active_connections[poll_id]:
            try:
                await ws.send_text(msg)
            except Exception:
                dead_conns.add(ws)
        active_connections[poll_id] -= dead_conns


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title='QuickPoll API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class CreatePollRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=300)
    options: List[str] = Field(..., min_items=2, max_items=10)
    allow_multiple: bool = False


class VoteRequest(BaseModel):
    option_ids: List[int] = Field(..., min_items=1)


def format_poll(poll: Poll):
    total_votes = sum(o.vote_count for o in poll.options)
    return {
        'id': poll.id,
        'question': poll.question,
        'allow_multiple': poll.allow_multiple,
        'total_votes': total_votes,
        'created_at': poll.created_at.isoformat(),
        'options': [
            {
                'id': o.id,
                'text': o.text,
                'votes': o.vote_count,
                'percentage': round((o.vote_count / total_votes * 100), 1) if total_votes > 0 else 0
            }
            for o in poll.options
        ]
    }


@app.post('/api/polls', status_code=201)
async def create_poll(req: CreatePollRequest, db: AsyncSession = Depends(get_db)):
    poll = Poll(
        id=generate_short_id(),
        question=req.question.strip(),
        allow_multiple=req.allow_multiple
    )
    for opt_text in req.options:
        if opt_text.strip():
            poll.options.append(PollOption(text=opt_text.strip()))

    db.add(poll)
    await db.commit()
    await db.refresh(poll, ['options'])
    return format_poll(poll)


@app.get('/api/polls/{poll_id}')
async def get_poll(poll_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Poll).options(selectinload(Poll.options)).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail='Poll not found')
    return format_poll(poll)


@app.post('/api/polls/{poll_id}/vote')
async def vote_poll(poll_id: str, req: VoteRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Poll).options(selectinload(Poll.options)).where(Poll.id == poll_id)
    )
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail='Poll not found')

    if not poll.allow_multiple and len(req.option_ids) > 1:
        raise HTTPException(status_code=400, detail='This poll allows only a single vote.')

    option_map = {o.id: o for o in poll.options}
    for opt_id in req.option_ids:
        if opt_id in option_map:
            option_map[opt_id].vote_count += 1

    await db.commit()
    await db.refresh(poll, ['options'])

    formatted = format_poll(poll)
    await broadcast_poll_update(poll_id, formatted)
    return formatted


@app.websocket('/ws/polls/{poll_id}')
async def poll_websocket(websocket: WebSocket, poll_id: str):
    await websocket.accept()
    if poll_id not in active_connections:
        active_connections[poll_id] = set()
    active_connections[poll_id].add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        active_connections[poll_id].discard(websocket)
