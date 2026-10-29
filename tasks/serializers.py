from typing import Any

from rest_framework import serializers
from rest_framework.request import Request

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    """Serialize task data and restrict employee updates."""

    class Meta:
        """Define the fields exposed by the task API."""

        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "created_at",
            "deadline",
            "assignee",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "created_by"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Ensure employees submit only the task status field."""
        request: Request | None = self.context.get("request")

        if request and request.user.is_authenticated and not request.user.is_staff:
            allowed_fields = {"status"}
            submitted_fields = set(self.initial_data.keys())

            if not submitted_fields.issubset(allowed_fields):
                raise serializers.ValidationError(
                    "Employees can only update task status."
                )

        return attrs
