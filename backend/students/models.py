from django.db import models

from common.models import TimeStampedModel
from common.validators import phone_validator


class Student(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        LEFT = "left", "Left hostel"

    enrollment_no = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=16, validators=[phone_validator])
    gender = models.CharField(max_length=10, choices=Gender.choices)
    address = models.TextField()
    guardian_name = models.CharField(max_length=150)
    guardian_phone = models.CharField(max_length=16, validators=[phone_validator])
    admission_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        ordering = ["full_name"]
        indexes = [models.Index(fields=["full_name"])]

    def __str__(self):
        return f"{self.enrollment_no} - {self.full_name}"

    @property
    def current_allocation(self):
        """The student's active room allocation, if any (one query per call)."""
        return self.allocations.filter(is_active=True).select_related("room").first()
