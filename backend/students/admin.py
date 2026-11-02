from django.contrib import admin

from students.models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("enrollment_no", "full_name", "email", "phone", "status", "admission_date")
    list_filter = ("status", "gender")
    search_fields = ("enrollment_no", "full_name", "email", "phone")

    def has_delete_permission(self, request, obj=None):
        # Students are deactivated (status), never deleted, to keep history intact.
        return False
