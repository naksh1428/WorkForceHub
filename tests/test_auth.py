"""Tests for signing up, logging in and protected routes."""
import unittest

from tests.base import ApiTestCase


class AuthTests(ApiTestCase):
    def test_register_returns_token(self) -> None:
        response = self.client.post(
            "/auth/register", json={"username": "alice", "password": "secret123"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["token_type"], "bearer")
        self.assertTrue(response.json()["access_token"])

    def test_register_duplicate_username_fails(self) -> None:
        self.register("alice")
        response = self.client.post(
            "/auth/register", json={"username": "alice", "password": "other1234"}
        )
        self.assertEqual(response.status_code, 409)

    def test_register_short_password_fails(self) -> None:
        response = self.client.post(
            "/auth/register", json={"username": "alice", "password": "short"}
        )
        self.assertEqual(response.status_code, 422)

    def test_login_success(self) -> None:
        self.register("alice", "secret123")
        response = self.client.post(
            "/auth/login", data={"username": "alice", "password": "secret123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_login_wrong_password_fails(self) -> None:
        self.register("alice", "secret123")
        response = self.client.post(
            "/auth/login", data={"username": "alice", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, 401)

    def test_protected_route_without_token_fails(self) -> None:
        response = self.client.get("/employees")
        self.assertEqual(response.status_code, 401)

    def test_protected_route_with_bad_token_fails(self) -> None:
        response = self.client.get(
            "/employees", headers={"Authorization": "Bearer not-a-real-token"}
        )
        self.assertEqual(response.status_code, 401)


class HealthTests(ApiTestCase):
    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"api": "up", "redis": "up"})


if __name__ == "__main__":
    unittest.main()
