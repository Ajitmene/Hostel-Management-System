from django.contrib import admin

from fees.models import FeeStructure, Payment, StudentFee


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "frequency", "is_active")
    list_filter = ("frequency", "is_active")
    search_fields = ("name",)


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = ("student", "structure", "amount_due", "amount_paid", "balance", "due_date", "status")
    list_filter = ("structure", "due_date")
    search_fields = ("student__enrollment_no", "student__full_name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Payments are append-only: they can be added and viewed, never edited or deleted."""

    list_display = ("receipt_number", "fee", "amount", "payment_date", "method", "recorded_by")
    list_filter = ("method", "payment_date")
    search_fields = ("receipt_number", "transaction_reference", "fee__student__enrollment_no")
    readonly_fields = ("receipt_number", "recorded_by")
    exclude = ("idempotency_key",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return obj is None

    def has_delete_permission(self, request, obj=None):
        return False
