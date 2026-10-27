from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsManagerOrAssignedEmployee(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        if request.method in SAFE_METHODS:
            return obj.assignee_id == request.user.id

        return request.method == "PATCH" and obj.assignee_id == request.user.id
