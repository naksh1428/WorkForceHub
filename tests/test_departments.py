"""Tests for the department routes."""
import unittest

from tests.base import ApiTestCase


class DepartmentTests(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.headers = self.auth_headers()

    def test_create_and_list_departments(self) -> None:
        response = self.client.post(
            "/departments", json={"name": "Engineering"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Engineering")
        self.assertEqual(response.json()["employee_count"], 0)

        response = self.client.get("/departments", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([d["name"] for d in response.json()], ["Engineering"])

    def test_create_duplicate_department_fails(self) -> None:
        self.client.post("/departments", json={"name": "Sales"}, headers=self.headers)
        response = self.client.post(
            "/departments", json={"name": "Sales"}, headers=self.headers
        )
        self.assertEqual(response.status_code, 409)

    def test_delete_department(self) -> None:
        dept_id = self.client.post(
            "/departments", json={"name": "Sales"}, headers=self.headers
        ).json()["id"]

        response = self.client.delete(f"/departments/{dept_id}", headers=self.headers)
        self.assertEqual(response.status_code, 204)

        response = self.client.get("/departments", headers=self.headers)
        self.assertEqual(response.json(), [])

    def test_delete_missing_department_fails(self) -> None:
        response = self.client.delete("/departments/999", headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_new_department_clears_cached_list(self) -> None:
        self.client.get("/departments", headers=self.headers)
        self.assertIsNotNone(self.redis.get("departments:all"))

        self.client.post("/departments", json={"name": "HR"}, headers=self.headers)
        self.assertIsNone(self.redis.get("departments:all"))


if __name__ == "__main__":
    unittest.main()
