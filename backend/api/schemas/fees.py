from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common import Money, MoneyOut

Frequency = Literal["monthly", "semester", "yearly", "one_time"]
Method = Literal["cash", "upi", "card", "bank_transfer", "cheque"]
FeeStatus = Literal["pending", "partial", "paid", "overdue"]


class FeeStructureCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    amount: Money
    frequency: Frequency
    description: str = Field(default="", max_length=1000)

    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Monthly hostel fee", "amount": "4500.00", "frequency": "monthly"}]})


class FeeStructureOut(BaseModel):
    id: int
    name: str
    amount: MoneyOut
    frequency: str
    description: str
    is_active: bool


class StudentFeeCreate(BaseModel):
    student_id: int = Field(gt=0)
    structure_id: int = Field(gt=0)
    due_date: date
    amount_due: Money | None = None  # defaults to the structure's amount
    description: str = Field(default="", max_length=200)

    model_config = ConfigDict(json_schema_extra={"examples": [{"student_id": 1, "structure_id": 1, "due_date": "2026-11-10", "description": "November 2026"}]})


class StudentFeeOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    enrollment_no: str
    structure_id: int
    structure_name: str
    description: str
    amount_due: MoneyOut
    amount_paid: MoneyOut
    balance: MoneyOut
    due_date: date
    status: str


class PaymentCreate(BaseModel):
    fee_id: int = Field(gt=0)
    amount: Money
    payment_date: date
    method: Method
    transaction_reference: str | None = Field(default=None, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9\-_]+$",
                                 description="Unique per submission; resending the same key never double-charges.")

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "fee_id": 1, "amount": "2000.00", "payment_date": "2026-11-02", "method": "upi",
        "transaction_reference": "UPI-8842193", "idempotency_key": "pay-2026-11-02-0001",
    }]})


class PaymentOut(BaseModel):
    id: int
    receipt_number: str
    fee_id: int
    student_id: int
    student_name: str
    enrollment_no: str
    amount: MoneyOut
    payment_date: date
    method: str
    transaction_reference: str | None
    recorded_by: str
    created_at: datetime


class ReceiptOut(PaymentOut):
    fee_description: str
    structure_name: str
    amount_due: MoneyOut
    total_paid: MoneyOut
    balance_after: MoneyOut


class FeeSummary(BaseModel):
    total_fees: int
    total_due: MoneyOut
    total_collected: MoneyOut
    outstanding: MoneyOut
    overdue_count: int
    overdue_amount: MoneyOut
    pending_count: int
    partial_count: int
    paid_count: int
    collected_this_month: MoneyOut
    payments_this_month: int
    payments_total: int
