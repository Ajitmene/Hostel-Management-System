from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Attendance(TimeStampedModel):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LEAVE = "leave", "Leave"

    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="attendance_records")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_attendance")
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date", "student_id"]
        verbose_name_plural = "attendance records"
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="one_attendance_per_student_per_day"),
        ]
        indexes = [models.Index(fields=["date", "status"])]

    def __str__(self):
        return f"{self.student_id} {self.date} {self.status}"
