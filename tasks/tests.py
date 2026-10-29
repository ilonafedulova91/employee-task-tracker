from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Task

User = get_user_model()


class TaskAPITests(APITestCase):
    """Test task API permissions, validation, filtering, search, and ordering."""

    def setUp(self):
        """Create test users and an initial task."""
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

    def get_results(self, response):
        """Return API results with or without pagination."""
        data = response.data
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    def test_unauthenticated_user_cannot_list_tasks(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_list_all_tasks(self):
        Task.objects.create(
            title="Other employee task",
            assignee=self.other_employee,
            created_by=self.manager,
        )
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(self.get_results(response)), 2)

    def test_employee_can_list_assigned_tasks(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.task.id)

    def test_employee_cannot_see_another_employees_task(self):
        self.client.force_authenticate(user=self.other_employee)

        response = self.client.get(reverse("task-detail", kwargs={"pk": self.task.pk}))

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

    def test_employee_cannot_delete_task(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_employee_cannot_use_put(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.put(
            self.detail_url,
            {
                "title": "Replacement title",
                "description": "Replacement description",
                "status": Task.Status.IN_PROGRESS,
                "priority": Task.Priority.LOW,
                "assignee": self.employee.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_update_status_and_title_together(self):
        self.client.force_authenticate(user=self.employee)

        response = self.client.patch(
            self.detail_url,
            {
                "status": Task.Status.IN_PROGRESS,
                "title": "Changed title",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.PENDING)
        self.assertEqual(self.task.title, "Complete report")

    def test_manager_can_filter_tasks_by_status(self):
        Task.objects.create(
            title="Completed task",
            status=Task.Status.COMPLETED,
            assignee=self.other_employee,
            created_by=self.manager,
        )
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(
            self.url,
            {"status": Task.Status.COMPLETED},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Completed task")

    def test_manager_can_filter_tasks_by_priority(self):
        Task.objects.create(
            title="Low priority task",
            priority=Task.Priority.LOW,
            assignee=self.other_employee,
            created_by=self.manager,
        )
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(
            self.url,
            {"priority": Task.Priority.LOW},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Low priority task")

    def test_manager_can_filter_tasks_by_assignee(self):
        Task.objects.create(
            title="Other employee task",
            assignee=self.other_employee,
            created_by=self.manager,
        )
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(
            self.url,
            {"assignee": self.other_employee.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Other employee task")

    def test_manager_can_search_tasks_by_title(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.url, {"search": "Complete report"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.task.id)

    def test_manager_can_search_tasks_by_description(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.url, {"search": "monthly report"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.task.id)

    def test_manager_can_order_tasks_by_deadline(self):
        now = timezone.now()
        later_task = Task.objects.create(
            title="Later deadline",
            deadline=now + timedelta(days=5),
            assignee=self.employee,
            created_by=self.manager,
        )
        earlier_task = Task.objects.create(
            title="Earlier deadline",
            deadline=now + timedelta(days=1),
            assignee=self.employee,
            created_by=self.manager,
        )
        self.client.force_authenticate(user=self.manager)

        response = self.client.get(self.url, {"ordering": "deadline"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        result_ids = [item["id"] for item in results]
        self.assertLess(
            result_ids.index(earlier_task.id),
            result_ids.index(later_task.id),
        )

    def test_manager_cannot_create_task_without_title(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {"description": "A task without a title"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Task.objects.filter(title="").exists())

    def test_manager_cannot_create_task_with_invalid_status(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {
                "title": "Invalid status task",
                "status": "invalid_status",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manager_cannot_create_task_with_invalid_priority(self):
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            self.url,
            {
                "title": "Invalid priority task",
                "priority": "urgent_and_important",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_schema_endpoint_is_available(self):
        response = self.client.get(reverse("schema"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_documentation_endpoint_is_available(self):
        response = self.client.get(reverse("swagger-ui"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
