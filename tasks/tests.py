
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Task

User = get_user_model()


class TaskAPITests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="manager",
            password="TestPass123!",
            is_staff=True,
        )
        self.employee = User.objects.create_user(
            username="employee",
            password="TestPass123!",
        )
        self.other_employee = User.objects.create_user(
            username="other",
            password="TestPass123!",
        )

        self.task = Task.objects.create(
            title="Complete report",
            description="Prepare the monthly report",
            status=Task.Status.PENDING,
            priority=Task.Priority.HIGH,
            assignee=self.employee,
            created_by=self.manager,
        )

        self.url = reverse("task-list")
        self.detail_url = reverse(
            "task-detail",
            kwargs={"pk": self.task.pk},
        )

    def test_unauthenticated_user_cannot_list_tasks(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_list_all_tasks(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"] if isinstance(response.data, dict) and "count" in response.data else len(response.data), 1)

    def test_employee_can_list_assigned_tasks(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.task.id)

    def test_employee_cannot_see_another_employees_task(self):
        self.client.force_authenticate(user=self.other_employee)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_can_create_task(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {
                "title": "Prepare presentation",
                "description": "Prepare slides",
                "priority": Task.Priority.MEDIUM,
                "assignee": self.employee.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(
            Task.objects.latest("id").created_by,
            self.manager,
        )

    def test_employee_cannot_create_task(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.post(
            self.url,
            {"title": "Unauthorized task"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_can_update_task_status(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.patch(
            self.detail_url,
            {"status": Task.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

    def test_employee_cannot_change_task_title(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.patch(
            self.detail_url,
            {"title": "Changed title"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Complete report")

    def test_manager_can_update_task(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            self.detail_url,
            {"title": "Updated report"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Updated report")

    def test_manager_can_delete_task(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
