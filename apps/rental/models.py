import math
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F
from django.db.models.constraints import UniqueConstraint, CheckConstraint
from django.db.models.enums import TextChoices
from django.db.models.fields import (
    CharField, DecimalField, PositiveIntegerField, TextField,
    BooleanField, DateTimeField,
)
from django.db.models.fields.related import ForeignKey
from django.conf import settings

from apps.abstracts.models import AbstractBaseModel

class Console(AbstractBaseModel):

    class Platform(models.TextChoices):
        PS4 = "PlayStation 4"
        PS5 = "PlayStation 5"

    class Status(models.TextChoices):
        AVAILABLE = "Available"
        MAINTENANCE = "In maintenance"
        RETIRED = "Retired"
        TAKEN = "Taken"

    name = CharField(max_length=100)
    platform = CharField(max_length=25, choices=Platform.choices)
    serial_number = CharField(max_length=100, unique=True)
    status = CharField(max_length=25, choices=Status.choices, default=Status.AVAILABLE)
    deposit = DecimalField(max_digits=10, decimal_places=2, default=2)
    gamepads_included = PositiveIntegerField(default=2)
    notes = TextField(blank=True)

    def is_free_between(self, start_at, end_at, exclude_rental=None):
        """True if no pending/active rental overlaps the given time period."""
        qs = RentalItem.objects.filter(
            console=self,
            rental__status__in=Rental.BLOCKING_STATUSES,
            rental__start_at__lt=end_at,
            rental__end_at__gt=start_at,
        )
        if exclude_rental is not None:
            qs = qs.exclude(rental=exclude_rental)
        return not qs.exists()


    class Meta:
        ordering = ['platform', 'name']

    def __str__(self):
        return f"{self.name} ({self.platform})"

class ConsolePrice(AbstractBaseModel):
    console = ForeignKey(Console, on_delete=models.CASCADE, related_name='prices')
    name = CharField(max_length=50)
    duration_minutes = PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = BooleanField(default=True)

    class Meta:
        ordering = ['console', 'duration_minutes']
        constraints = [
            UniqueConstraint(
                fields=['console', 'duration_minutes'],
                name = 'unique_duration_per_console'
            )
        ]

    def __str__(self):
        return f"{self.console.name} = {self.name}: {self.price}"

class Rental(AbstractBaseModel):
    class Status(TextChoices):
        PENDING = "Pending"
        ACTIVE = "Active"
        COMPLETED = "Completed"
        CANCELED = "Canceled"

    BLOCKING_STATUSES = [
        Status.PENDING,
        Status.ACTIVE,
    ]

    customer = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='rentals',
        null=True,
        blank=True,
    )
    customer_name = CharField(max_length=100, blank=True, help_text='Walk-in customer name')
    customer_phone = CharField(max_length=20, blank=True, help_text='Walk-in customer phone')

    status = CharField(max_length=25, choices=Status.choices, default=Status.PENDING)
    start_at = DateTimeField()
    end_at = DateTimeField()
    returned_at = DateTimeField(null=True, blank=True)
    delivery_address = TextField(blank=True)
    deposit_amount = DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = TextField(blank=True)

    class Meta:
        ordering = ['-start_at']


        constraints = [
            CheckConstraint(
                condition=Q(end_at__gt=F('start_at')),
                name="rental_end_after_start"
            )
        ]

    def __str__(self):
        name = self.customer or self.customer_name or 'Walk-in'
        return f"#{self.pk} - {name} ({self.get_status_display()})"

    def clean(self):
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValidationError("End date must be after start date.")

    @property
    def billable_end(self):
        return self.returned_at or self.end_at

    @property
    def total_price(self):
        return sum((item.subtotal for item in self.items.all()), Decimal("0"))
    @property
    def duration_minutes(self):
        """Total rental duration in minutes."""
        delta = self.billable_end - self.start_at
        return delta.total_seconds() / 60


class RentalItem(AbstractBaseModel):
    rental = models.ForeignKey(
        Rental, on_delete=models.CASCADE, related_name='items',
    )
    console = ForeignKey(Console, on_delete=models.CASCADE, related_name='rental_items')
    pricing = ForeignKey(
        ConsolePrice,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rental_items',
    )
    unit_minutes = PositiveIntegerField()
    unit_price = DecimalField(max_digits=10, decimal_places=2)
    returned_at = DateTimeField(null=True, blank=True)
    condition_notes = TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['rental', 'console'],
                name='unique_console_per_rental',
            ),
        ]


    def __str__(self):
        return f"{self.console} in rental {self.rental_id}"

    @property
    def units(self):
        """
        Number of pricing units to charge, round up, minimum 1
        """
        return max(1, math.ceil(self.rental.duration_minutes / self.unit_minutes))

    @property
    def subtotal(self):
        return self.unit_price * self.units


    def clean(self):
        if self.pricing and self.pricing.console_id != self.console_id:
            raise ValidationError("pricing: This price belongs to another console")
        if self.pricing and not self.pricing.is_active:
            raise ValidationError("pricing: This pricing is not active")
        if self.console.status != Console.Status.AVAILABLE:
            raise ValidationError("console: This console is not available")
        if not self.console.is_free_between(
            self.rental.start_at,
            self.rental.end_at,
            exclude_rental=self.rental):
            raise ValidationError("console: This console is not available")
