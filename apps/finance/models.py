from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import (
    CharField,
    DecimalField,
    DateTimeField,
    TextField,
    ForeignKey,
    PositiveIntegerField,
)
from django.db.models.constraints import CheckConstraint
from django.db.models.enums import TextChoices
from django.db.models import Q, F

from apps.abstracts.models import AbstractBaseModel


class Invoice(AbstractBaseModel):
    """Invoice generated for a rental."""

    class Status(TextChoices):
        DRAFT = "Draft"
        ISSUED = "Issued"
        PAID = "Paid"
        CANCELED = "Canceled"

    rental = ForeignKey(
        'rental.Rental',
        on_delete=models.CASCADE,
        related_name='invoices',
    )
    customer = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='invoices',
        null=True,
        blank=True,
    )
    customer_name = CharField(max_length=100, blank=True, help_text='Walk-in customer name')
    status = CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    total_amount = DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    issued_at = DateTimeField(null=True, blank=True)
    due_at = DateTimeField(null=True, blank=True)
    notes = TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        name = self.customer or self.customer_name or 'Walk-in'
        return f"Invoice #{self.pk} - {name} ({self.get_status_display()})"


class Payment(AbstractBaseModel):
    """Payment record against an invoice."""

    class Method(TextChoices):
        CASH = "Cash"
        CARD = "Card"
        TRANSFER = "Transfer"

    class Status(TextChoices):
        PENDING = "Pending"
        COMPLETED = "Completed"
        FAILED = "Failed"
        REFUNDED = "Refunded"

    invoice = ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount = DecimalField(max_digits=10, decimal_places=2)
    method = CharField(max_length=25, choices=Method.choices)
    status = CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reference = CharField(max_length=100, blank=True)
    paid_at = DateTimeField(null=True, blank=True)
    notes = TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            CheckConstraint(
                condition=Q(amount__gt=0),
                name='payment_amount_positive',
            ),
        ]

    def __str__(self):
        return f"Payment #{self.pk} - {self.amount} ({self.get_status_display()})"
