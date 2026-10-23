import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.finance.models import Invoice, Payment
from apps.rental.models import Rental


class Command(BaseCommand):
    """Create invoices and payments for rentals that don't have them yet."""

    help = "Create test invoices and payments for existing rentals."

    INVOICE_STATUS: dict[str, str] = {
        Rental.Status.COMPLETED: Invoice.Status.PAID,
        Rental.Status.ACTIVE: Invoice.Status.ISSUED,
        Rental.Status.PENDING: Invoice.Status.DRAFT,
    }
    PAYMENT_METHODS: dict[str, str] = {
        "CLICK": Payment.Method.TRANSFER,
        "PAYME": Payment.Method.TRANSFER,
        "UZCARD": Payment.Method.CARD,
        "HUMO": Payment.Method.CARD,
        "CASH": Payment.Method.CASH,
    }

    def handle(self, *args: Any, **options: Any) -> None:
        """Command entry point."""
        rentals: list[Rental] = list(
            Rental.objects.filter(
                deleted_at__isnull=True,
                status__in=list(self.INVOICE_STATUS),
                invoices__isnull=True,
            )
            .select_related("customer")
            .prefetch_related("items")
        )
        if not rentals:
            self.stdout.write(
                self.style.WARNING(
                    "Nothing new to create. Run seed_rental first if there are no rentals."
                )
            )
            return

        with transaction.atomic():
            invoices: list[Invoice] = self.__create_invoices(rentals)
            payments: list[Payment] = self.__create_payments(invoices)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(invoices)} invoices and {len(payments)} payments."
            )
        )

    def __create_invoices(self, rentals: list[Rental]) -> list[Invoice]:
        """Create one invoice per rental, its status following the rental's."""
        new_invoices: list[Invoice] = []
        for rental in rentals:
            status: str = self.INVOICE_STATUS[rental.status]
            issued_at: datetime | None = None
            due_at: datetime | None = None
            if status != Invoice.Status.DRAFT:
                issued_at = rental.start_at
                due_at = rental.end_at + timedelta(days=1)

            new_invoices.append(
                Invoice(
                    rental=rental,
                    customer=rental.customer,
                    customer_name="" if rental.customer else rental.customer_name,
                    status=status,
                    total_amount=rental.total_price,
                    issued_at=issued_at,
                    due_at=due_at,
                )
            )

        Invoice.objects.bulk_create(new_invoices)
        return new_invoices

    def __create_payments(self, invoices: list[Invoice]) -> list[Payment]:
        """Paid invoices get a completed payment, issued ones a pending one."""
        new_payments: list[Payment] = []
        for invoice in invoices:
            if invoice.status == Invoice.Status.DRAFT or invoice.total_amount <= Decimal("0"):
                continue

            prefix: str = random.choice(list(self.PAYMENT_METHODS))
            payment: Payment = Payment(
                invoice=invoice,
                amount=invoice.total_amount,
                method=self.PAYMENT_METHODS[prefix],
                reference=f"{prefix}-{random.randint(100000, 999999)}",
            )
            if invoice.status == Invoice.Status.PAID:
                payment.status = Payment.Status.COMPLETED
                payment.paid_at = invoice.rental.billable_end
            new_payments.append(payment)

        Payment.objects.bulk_create(new_payments)
        return new_payments
