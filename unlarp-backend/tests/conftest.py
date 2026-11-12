import os
import sys
import tempfile
from pathlib import Path

# Point the app at a throwaway database and media folder before it is imported.
_tmp = tempfile.mkdtemp(prefix="unlarp-test-")
os.environ["UNLARP_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UNLARP_MEDIA_DIR"] = f"{_tmp}/media"
os.environ["UNLARP_DAILY_GENERATION_LIMIT"] = "3"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def make_user(client):
    """Sign up a user and return auth headers for them."""

    def _make(username: str, with_selfie: bool = True) -> dict:
        r = client.post(
            "/auth/signup",
            json={
                "username": username,
                "email": f"{username}@example.com",
                "password": "correct-horse-battery",
            },
        )
        assert r.status_code == 201, r.text
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        if with_selfie:
            r = client.post(
                "/users/me/selfies",
                headers=headers,
                files={"file": ("me.png", b"\x89PNG fake image bytes", "image/png")},
            )
            assert r.status_code == 201, r.text
        return headers

    return _make
