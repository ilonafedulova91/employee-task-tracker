from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "priority",
        "assignee",
        "created_by",
        "deadline",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "description")
    list_select_related = ("assignee", "created_by")
    ordering = ("-created_at",)
