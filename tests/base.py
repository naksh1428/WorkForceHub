"""Shared setup for the tests.

Each test gets an empty in-memory SQLite database and a fake Redis,
so no real MySQL or Redis server is needed.
"""
import os
import unittest

# Settings are read when the app is imported, so set them first.
# These win over the values in the .env file.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-at-least-32-bytes-long"

import fakeredis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import cache  # noqa: E402
from app.db.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# StaticPool keeps one connection, so every session sees the same in-memory database
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Give routes a session on the test database instead of the real one."""
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


class ApiTestCase(unittest.TestCase):
    """Base class for API tests. Gives a fresh database, fake Redis and a client."""

    def setUp(self) -> None:
        Base.metadata.create_all(bind=engine)
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        cache.set_client(self.redis)
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        cache.set_client(None)
        Base.metadata.drop_all(bind=engine)

    def register(self, username: str = "alice", password: str = "secret123") -> str:
        """Create a user and give back their login token."""
        response = self.client.post(
            "/auth/register", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["access_token"]

    def auth_headers(self) -> dict[str, str]:
        """Headers for a logged-in user."""
        return {"Authorization": f"Bearer {self.register()}"}
