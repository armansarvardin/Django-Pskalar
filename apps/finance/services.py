from decimal import Decimal
from django.db.models import Sum
from apps.finance.models import Payment, PaymentMethod
from django.utils import timezone

def expected_cash(shift):
    cash_in = shift.payments.filter(
        status=Payment.Status.PAID,
        method__code=PaymentMethod.Code.CASH,
        deleted_at__isnull=True,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    cash_out = shift.expenses.filter(
        paid_from_cash=True,
        deleted_at__isnull=True,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return shift.opening_cash + cash_in - cash_out

def cash_difference(shift):
    if shift.closing is None:
        return None
    return shift.closing - expected_cash(shift)

def calculate_commission(amount, method):
    commission = amount * method.commission_percent / Decimal("100")
    return commission.quantize(Decimal("0.01"))

def prepare_payment(payment):
    payment.commission_amount = calculate_commission(payment.amount, payment.method)
    if payment.status == Payment.Status.PAID and payment.paid_at is None:
        payment.paid_at = timezone.now()