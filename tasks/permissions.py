from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsManagerOrAssignedEmployee(BasePermission):
    """Restrict task access to managers and assigned employees."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Allow access only to authenticated users."""
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any,
    ) -> bool:
        """Allow managers full access and employees limited task access."""
        if request.user.is_staff:
            return True

        if request.method in SAFE_METHODS:
            return obj.assignee_id == request.user.id

        return request.method == "PATCH" and obj.assignee_id == request.user.id
