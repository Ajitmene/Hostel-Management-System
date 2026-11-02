from django.contrib import admin

from attendance.models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "status", "recorded_by")
    list_filter = ("status", "date")
    search_fields = ("student__enrollment_no", "student__full_name")
    readonly_fields = ("recorded_by",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)
