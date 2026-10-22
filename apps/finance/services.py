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


def get_open_shift():
    """The currently open shift, or None."""
    return Shift.objects.filter(
        status=Shift.Status.OPEN,
        deleted_at__isnull=True,
    ).first()


def paid_total(rental):
    """How much was already paid for this rental."""
    return rental.payments.filter(
        status=Payment.Status.PAID,
        deleted_at__isnull=True,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")



def close_shift(shift, closing):
    """Close the shift with the counted cash."""
    shift.closing = closing
    shift.closed_at = timezone.now()
    shift.status = Shift.Status.CLOSED
    shift.save()


def refund_payment(payment):
    """Mark a payment as refunded. The row stays for history."""
    payment.status = Payment.Status.REFUNDED
    payment.save()