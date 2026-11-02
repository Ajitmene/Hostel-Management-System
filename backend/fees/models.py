import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from common.models import TimeStampedModel

ZERO = Decimal("0.00")
MIN_AMOUNT = Decimal("0.01")


def generate_receipt_number() -> str:
    return "RCP-" + uuid.uuid4().hex[:12].upper()


def generate_idempotency_key() -> str:
    return uuid.uuid4().hex


class FeeStructure(TimeStampedModel):
    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        SEMESTER = "semester", "Per semester"
        YEARLY = "yearly", "Yearly"
        ONE_TIME = "one_time", "One time"

    name = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(MIN_AMOUNT)])
    frequency = models.CharField(max_length=20, choices=Frequency.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StudentFee(TimeStampedModel):
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="fees")
    structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, related_name="student_fees")
    description = models.CharField(max_length=200, blank=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(MIN_AMOUNT)])
    due_date = models.DateField(db_index=True)

    class Meta:
        ordering = ["-due_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["student", "structure", "due_date"], name="unique_fee_per_student_period"),
            models.CheckConstraint(condition=Q(amount_due__gte=MIN_AMOUNT), name="studentfee_amount_positive"),
        ]

    def __str__(self):
        return f"Fee #{self.pk} student={self.student_id} due={self.amount_due}"

    # Paid amount, balance and status are derived from payments, so they cannot drift.
    @property
    def amount_paid(self) -> Decimal:
        return self.payments.aggregate(total=Sum("amount"))["total"] or ZERO

    @property
    def balance(self) -> Decimal:
        return self.amount_due - self.amount_paid

    @property
    def status(self) -> str:
        paid = self.amount_paid
        if paid >= self.amount_due:
            return "paid"
        if self.due_date < timezone.localdate():
            return "overdue"
        return "partial" if paid > ZERO else "pending"


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        CHEQUE = "cheque", "Cheque"

    fee = models.ForeignKey(StudentFee, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(MIN_AMOUNT)])
    payment_date = models.DateField()
    method = models.CharField(max_length=20, choices=Method.choices)
    # NULL (not "") when absent, so the unique index only applies to real references.
    transaction_reference = models.CharField(max_length=100, null=True, blank=True, unique=True)
    receipt_number = models.CharField(max_length=30, unique=True, default=generate_receipt_number, editable=False)
    # Client-supplied key that makes a repeated submission a no-op (used by the API).
    idempotency_key = models.CharField(max_length=64, unique=True, default=generate_idempotency_key)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_payments")

    class Meta:
        ordering = ["-payment_date", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=MIN_AMOUNT), name="payment_amount_positive"),
        ]

    def __str__(self):
        return f"{self.receipt_number} ({self.amount})"

    def save(self, *args, **kwargs):
        self.transaction_reference = (self.transaction_reference or "").strip() or None
        super().save(*args, **kwargs)
