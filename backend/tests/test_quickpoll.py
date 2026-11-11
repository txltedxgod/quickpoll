"""Unit and integration tests for QuickPoll validation, deduplicated voting, and health."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import database
import main as poll_main
import pytest
from fastapi.testclient import TestClient
from models import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture()
def poll_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    db_file = tmp_path / "quickpoll_test.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file.as_posix()}")
    test_session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "async_session", test_session_maker)

    async def test_init_db() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(database, "init_db", test_init_db)

    application = poll_main.create_app()
    with TestClient(application) as client:
        yield client


def test_poll_creation_validation_and_single_choice_voting(poll_client: TestClient) -> None:
    assert poll_client.get("/health").json() == {"status": "healthy"}

    # Blank / duplicate options must be rejected with 422
    bad = poll_client.post(
        "/api/polls",
        json={"question": "Best DB?", "options": ["Postgres", "postgres", "   "]},
    )
    assert bad.status_code == 422

    created = poll_client.post(
        "/api/polls",
        json={
            "question": "Preferred runtime?",
            "options": ["Rust", "Python", "Go"],
            "allow_multiple": False,
        },
    )
    assert created.status_code == 201
    poll = created.json()
    poll_id = poll["id"]
    opt_ids = [o["id"] for o in poll["options"]]

    # Single-choice poll rejects voting for multiple distinct options
    multi_reject = poll_client.post(
        f"/api/polls/{poll_id}/vote",
        json={"option_ids": [opt_ids[0], opt_ids[1]]},
    )
    assert multi_reject.status_code == 400

    # Non-existent option IDs are rejected cleanly instead of silent 200 OK
    bad_opt = poll_client.post(
        f"/api/polls/{poll_id}/vote",
        json={"option_ids": [999999]},
    )
    assert bad_opt.status_code == 400

    voted = poll_client.post(
        f"/api/polls/{poll_id}/vote",
        json={"option_ids": [opt_ids[0]]},
    )
    assert voted.status_code == 200
    assert voted.json()["total_votes"] == 1
    assert voted.json()["options"][0]["percentage"] == 100.0


def test_multi_choice_poll_deduplicates_repeated_option_ids(poll_client: TestClient) -> None:
    created = poll_client.post(
        "/api/polls",
        json={
            "question": "Pick languages",
            "options": ["TypeScript", "SQL", "Rust"],
            "allow_multiple": True,
        },
    )
    assert created.status_code == 201
    poll = created.json()
    first_id = poll["options"][0]["id"]
    second_id = poll["options"][1]["id"]

    # Repeated option ID in a single request must count only once per option
    voted = poll_client.post(
        f"/api/polls/{poll['id']}/vote",
        json={"option_ids": [first_id, first_id, second_id]},
    )
    assert voted.status_code == 200
    body = voted.json()
    assert body["total_votes"] == 2
    assert body["options"][0]["votes"] == 1
    assert body["options"][1]["votes"] == 1
