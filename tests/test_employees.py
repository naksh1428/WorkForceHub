"""Tests for the employee routes."""
import unittest

from tests.base import ApiTestCase


class EmployeeTests(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.headers = self.auth_headers()
        self.dept_id = self.client.post(
            "/departments", json={"name": "Engineering"}, headers=self.headers
        ).json()["id"]

    def create_employee(self, **overrides) -> dict:
        """Add an employee and give back the response body."""
        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@example.com",
            "job_title": "Developer",
            "salary": "50000.00",
            "hire_date": "2024-01-15",
            "department_id": self.dept_id,
        }
        payload.update(overrides)
        response = self.client.post("/employees", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_and_get_employee(self) -> None:
        employee = self.create_employee()

        response = self.client.get(f"/employees/{employee['id']}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "jane@example.com")

    def test_create_employee_unknown_department_fails(self) -> None:
        response = self.client.post(
            "/employees",
            json={
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
                "job_title": "Developer",
                "salary": "50000.00",
                "hire_date": "2024-01-15",
                "department_id": 999,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_create_employee_duplicate_email_fails(self) -> None:
        self.create_employee()
        response = self.client.post(
            "/employees",
            json={
                "first_name": "John",
                "last_name": "Smith",
                "email": "jane@example.com",
                "job_title": "Tester",
                "salary": "40000.00",
                "hire_date": "2024-02-01",
                "department_id": self.dept_id,
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 409)

    def test_get_missing_employee_fails(self) -> None:
        response = self.client.get("/employees/999", headers=self.headers)
        self.assertEqual(response.status_code, 404)

    def test_list_employees_with_pagination(self) -> None:
        for i in range(3):
            self.create_employee(email=f"user{i}@example.com")

        response = self.client.get(
            "/employees", params={"page": 1, "page_size": 2}, headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertEqual(len(body["items"]), 2)

    def test_list_employees_search(self) -> None:
        self.create_employee(first_name="Jane", email="jane@example.com")
        self.create_employee(first_name="Bob", email="bob@example.com")

        response = self.client.get(
            "/employees", params={"search": "bob"}, headers=self.headers
        )
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["items"][0]["first_name"], "Bob")

    def test_update_employee(self) -> None:
        employee = self.create_employee()

        response = self.client.patch(
            f"/employees/{employee['id']}",
            json={"job_title": "Senior Developer"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_title"], "Senior Developer")
        self.assertEqual(response.json()["first_name"], "Jane")

    def test_update_clears_cached_employee(self) -> None:
        employee = self.create_employee()
        self.client.get(f"/employees/{employee['id']}", headers=self.headers)

        self.client.patch(
            f"/employees/{employee['id']}",
            json={"job_title": "Lead"},
            headers=self.headers,
        )
        response = self.client.get(f"/employees/{employee['id']}", headers=self.headers)
        self.assertEqual(response.json()["job_title"], "Lead")

    def test_delete_employee(self) -> None:
        employee = self.create_employee()

        response = self.client.delete(f"/employees/{employee['id']}", headers=self.headers)
        self.assertEqual(response.status_code, 204)

        response = self.client.get(f"/employees/{employee['id']}", headers=self.headers)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
