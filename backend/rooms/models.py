from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from common.models import TimeStampedModel


class Room(TimeStampedModel):
    class RoomType(models.TextChoices):
        SINGLE = "single", "Single"
        DOUBLE = "double", "Double"
        TRIPLE = "triple", "Triple"
        DORMITORY = "dormitory", "Dormitory"

    room_number = models.CharField(max_length=20, unique=True)
    room_type = models.CharField(max_length=20, choices=RoomType.choices)
    block = models.CharField(max_length=50)
    floor = models.PositiveSmallIntegerField(default=0)
    capacity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    monthly_rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    # False means closed (for example, under maintenance). Occupancy is NOT stored;
    # it is always computed from active allocations so it can never drift.
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["block", "room_number"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name="room_capacity_at_least_one"),
            models.CheckConstraint(condition=Q(monthly_rate__gte=0), name="room_rate_not_negative"),
        ]

    def __str__(self):
        return f"{self.block}-{self.room_number}"

    @property
    def occupancy(self) -> int:
        return self.allocations.filter(is_active=True).count()

    @property
    def is_available(self) -> bool:
        return self.is_active and self.occupancy < self.capacity


class RoomAllocation(TimeStampedModel):
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="allocations")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="allocations")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # MySQL has no partial unique indexes. This column equals the student's id
    # while the allocation is active and NULL once it ends. A unique index on it
    # therefore allows only ONE active allocation per student (MySQL permits
    # many NULLs in a unique index). It is maintained in save().
    active_student_key = models.PositiveBigIntegerField(null=True, blank=True, unique=True, editable=False)

    class Meta:
        ordering = ["-start_date", "-id"]
        indexes = [models.Index(fields=["room", "is_active"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="allocation_end_not_before_start",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_active=True, end_date__isnull=True, active_student_key=F("student"))
                    | Q(is_active=False, active_student_key__isnull=True)
                ),
                name="allocation_active_state_consistent",
            ),
        ]

    def __str__(self):
        state = "active" if self.is_active else "ended"
        return f"{self.student_id} -> {self.room_id} ({state})"

    def save(self, *args, **kwargs):
        self.active_student_key = self.student_id if self.is_active else None
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"active_student_key"}
        super().save(*args, **kwargs)
