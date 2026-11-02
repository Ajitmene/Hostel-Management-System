from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from api.core.errors import ApiError
from api.services import audit
from fees.models import FeeStructure, Payment, StudentFee
from students.models import Student

ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=12, decimal_places=2)


def fee_queryset():
    return StudentFee.objects.select_related("student", "structure").annotate(
        paid=Coalesce(Sum("payments__amount"), Value(ZERO), output_field=MONEY)
    )


def derive_status(due, paid, due_date, today) -> str:
    if paid >= due:
        return "paid"
    if due_date < today:
        return "overdue"
    return "partial" if paid > 0 else "pending"


def filter_by_status(qs, status: str, today):
    return {
        "paid": lambda: qs.filter(paid__gte=F("amount_due")),
        "overdue": lambda: qs.filter(paid__lt=F("amount_due"), due_date__lt=today),
        "partial": lambda: qs.filter(paid__gt=0, paid__lt=F("amount_due"), due_date__gte=today),
        "pending": lambda: qs.filter(paid=0, due_date__gte=today),
    }[status]()


def serialize_fee(f: StudentFee, today=None) -> dict:
    today = today or timezone.localdate()
    return {
        "id": f.id, "student_id": f.student_id, "student_name": f.student.full_name,
        "enrollment_no": f.student.enrollment_no, "structure_id": f.structure_id,
        "structure_name": f.structure.name, "description": f.description, "amount_due": f.amount_due,
        "amount_paid": f.paid, "balance": f.amount_due - f.paid, "due_date": f.due_date,
        "status": derive_status(f.amount_due, f.paid, f.due_date, today),
    }


def get_fee_or_404(fee_id: int) -> StudentFee:
    fee = fee_queryset().filter(pk=fee_id).first()
    if not fee:
        raise ApiError(404, "not_found", "Fee record not found.")
    return fee


def serialize_structure(s: FeeStructure) -> dict:
    return {"id": s.id, "name": s.name, "amount": s.amount, "frequency": s.frequency,
            "description": s.description, "is_active": s.is_active}


def create_structure(data: dict, actor, ip=None) -> FeeStructure:
    if FeeStructure.objects.filter(name__iexact=data["name"]).exists():
        raise ApiError(409, "duplicate", "A fee structure with this name already exists.")
    with transaction.atomic():
        s = FeeStructure.objects.create(**data)
        audit.record(actor, "fee_structure.create", "fee_structure", s.id, {"name": s.name}, ip)
    return s


def create_fee(data: dict, actor, ip=None) -> StudentFee:
    student = Student.objects.filter(pk=data["student_id"]).first()
    if not student:
        raise ApiError(404, "not_found", "Student not found.")
    structure = FeeStructure.objects.filter(pk=data["structure_id"], is_active=True).first()
    if not structure:
        raise ApiError(404, "not_found", "Active fee structure not found.")
    amount = data.get("amount_due") or structure.amount
    try:
        with transaction.atomic():
            fee = StudentFee.objects.create(
                student=student, structure=structure, amount_due=amount,
                due_date=data["due_date"], description=data.get("description", ""),
            )
            audit.record(actor, "fee.create", "fee", fee.id,
                         {"student_id": student.id, "amount_due": amount, "due_date": data["due_date"]}, ip)
    except IntegrityError:
        raise ApiError(409, "duplicate", "This fee was already created for the student and due date.")
    return get_fee_or_404(fee.id)


def payment_queryset():
    return Payment.objects.select_related("fee__student", "fee__structure", "recorded_by")


def serialize_payment(p: Payment) -> dict:
    return {
        "id": p.id, "receipt_number": p.receipt_number, "fee_id": p.fee_id, "student_id": p.fee.student_id,
        "student_name": p.fee.student.full_name, "enrollment_no": p.fee.student.enrollment_no,
        "amount": p.amount, "payment_date": p.payment_date, "method": p.method,
        "transaction_reference": p.transaction_reference, "recorded_by": p.recorded_by.email,
        "created_at": p.created_at,
    }


def serialize_receipt(p: Payment) -> dict:
    paid_through = Payment.objects.filter(fee_id=p.fee_id, id__lte=p.id).aggregate(t=Sum("amount"))["t"] or ZERO
    data = serialize_payment(p)
    data.update({
        "fee_description": p.fee.description, "structure_name": p.fee.structure.name,
        "amount_due": p.fee.amount_due, "total_paid": paid_through,
        "balance_after": p.fee.amount_due - paid_through,
    })
    return data


def record_payment(data: dict, actor, ip=None) -> tuple[Payment, bool]:
    """Record a payment. Returns (payment, created). Resubmitting the same
    idempotency key returns the original payment instead of charging twice."""
    key = data["idempotency_key"]

    def existing_for_key():
        found = payment_queryset().filter(idempotency_key=key).first()
        if found and (found.fee_id != data["fee_id"] or found.amount != data["amount"]):
            raise ApiError(409, "idempotency_conflict", "This idempotency key was already used for a different payment.")
        return found

    found = existing_for_key()
    if found:
        return found, False

    ref = (data.get("transaction_reference") or "").strip() or None
    try:
        with transaction.atomic():
            # Lock the fee row so concurrent payments for one fee are serialized.
            fee = StudentFee.objects.select_for_update().filter(pk=data["fee_id"]).first()
            if not fee:
                raise ApiError(404, "not_found", "Fee record not found.")
            if data["payment_date"] > timezone.localdate():
                raise ApiError(400, "invalid_date", "Payment date cannot be in the future.")
            if ref and Payment.objects.filter(transaction_reference=ref).exists():
                raise ApiError(409, "duplicate_reference", "This transaction reference was already recorded.")
            paid = fee.payments.aggregate(t=Sum("amount"))["t"] or ZERO
            balance = fee.amount_due - paid
            if balance <= 0:
                raise ApiError(409, "fee_already_paid", "This fee has already been paid in full.")
            if data["amount"] > balance:
                raise ApiError(409, "overpayment", f"Amount exceeds the outstanding balance of {balance}.")
            payment = Payment.objects.create(
                fee=fee, amount=data["amount"], payment_date=data["payment_date"], method=data["method"],
                transaction_reference=ref, idempotency_key=key, recorded_by=actor,
            )
            audit.record(actor, "payment.record", "payment", payment.id,
                         {"receipt": payment.receipt_number, "fee_id": fee.id, "amount": payment.amount}, ip)
    except IntegrityError:
        # Lost a race on the idempotency key or transaction reference.
        found = existing_for_key()
        if found:
            return found, False
        raise ApiError(409, "duplicate_reference", "This transaction reference was already recorded.")
    return payment_queryset().get(pk=payment.pk), True


def summary() -> dict:
    today = timezone.localdate()
    out = {"total_fees": 0, "total_due": ZERO, "total_collected": ZERO, "overdue_count": 0, "overdue_amount": ZERO,
           "pending_count": 0, "partial_count": 0, "paid_count": 0}
    plain = StudentFee.objects.annotate(paid=Coalesce(Sum("payments__amount"), Value(ZERO), output_field=MONEY))
    for fee in plain:
        out["total_fees"] += 1
        out["total_due"] += fee.amount_due
        out["total_collected"] += fee.paid
        status = derive_status(fee.amount_due, fee.paid, fee.due_date, today)
        if status == "overdue":
            out["overdue_amount"] += fee.amount_due - fee.paid
            out["overdue_count"] += 1
        else:
            out[f"{status}_count"] += 1
    out["outstanding"] = out["total_due"] - out["total_collected"]
    month = Payment.objects.filter(payment_date__gte=today.replace(day=1), payment_date__lte=today)
    agg = month.aggregate(t=Sum("amount"))
    out["collected_this_month"] = agg["t"] or ZERO
    out["payments_this_month"] = month.count()
    out["payments_total"] = Payment.objects.count()
    return out
