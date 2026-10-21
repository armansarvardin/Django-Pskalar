from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.constraints import CheckConstraint, UniqueConstraint
from django.db.models.enums import TextChoices
from django.db.models.fields import (
    BooleanField,
    CharField,
    DateTimeField,
    DecimalField,
    PositiveIntegerField,
    TextField,
)
from django.db.models.fields.related import ForeignKey

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

    def __str__(self) -> str:
        return self.name

    def is_free_between(
        self, start_at: datetime, end_at: datetime, exclude_rental: Rental | None = None
    ) -> bool:
        """Check overlapping pending/active rentals; adjacent intervals are allowed"""
        qs = RentalItem.objects.filter(
            console=self,
            deleted_at__isnull=True,
            rental__status__in=Rental.BLOCKING_STATUSES,
            rental__start_at__lt=end_at,
            rental__end_at__gt=start_at,
        )
        if exclude_rental is not None:
            qs = qs.exclude(rental=exclude_rental)
        return not qs.exists()

    class Meta:
        ordering = ["platform", "name"]


class ConsolePrice(AbstractBaseModel):
    console = ForeignKey(Console, on_delete=models.CASCADE, related_name="prices")
    name = CharField(max_length=50)
    duration_minutes = PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    is_active = BooleanField(default=True)

    class Meta:
        ordering = ["console", "duration_minutes"]
        constraints = [
            UniqueConstraint(
                fields=["console", "duration_minutes"],
                name="unique_duration_per_console",
            ),
            CheckConstraint(
                condition=Q(duration_minutes__gt=0), name="price_duration_positive"
            ),
            CheckConstraint(
                condition=Q(price__gte=0), name="console_price_nonnegative"
            ),
        ]

    def __str__(self) -> str:
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
        related_name="rentals",
    )

    status = CharField(max_length=25, choices=Status.choices, default=Status.PENDING)
    start_at = DateTimeField()
    end_at = DateTimeField()
    returned_at = DateTimeField(null=True, blank=True)
    delivery_address = TextField(blank=True)
    deposit_amount = DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = TextField(blank=True)

    class Meta:
        ordering = ["-start_at"]

        constraints = [
            CheckConstraint(
                condition=Q(end_at__gt=F("start_at")), name="rental_end_after_start"
            )
        ]

    def __str__(self) -> str:
        return "f{self.pk} - {self.customer} ({self.get_status_display()})"

    def clean(self) -> None:
        super().clean()
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValidationError({"end_at": "End date must be after start date"})

        if self.start_at and self.returned_at and self.returned_at < self.start_at:
            raise ValidationError({"returned_at": "Return cannot be before start"})

    @property
    def billable_end(self) -> datetime:
        return self.returned_at or self.end_at

    @property
    def duration_minutes(self) -> float:
        return (self.billable_end - self.start_at).total_seconds() / 60

    @property
    def total_price(self) -> Decimal:
        return sum(
            (item.subtotal for item in self.items.all() if item.deleted_at is None),
            Decimal("0"),
        )


class RentalItem(AbstractBaseModel):
    rental = models.ForeignKey(
        Rental,
        on_delete=models.CASCADE,
        related_name="items",
    )
    console = ForeignKey(Console, on_delete=models.CASCADE, related_name="rental_items")
    pricing = ForeignKey(
        ConsolePrice,
        on_delete=models.SET_NULL,
        null=True,
        related_name="rental_items",
    )
    unit_minutes = PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    returned_at = DateTimeField(null=True, blank=True)
    condition_notes = TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["rental", "console"], name="unique_console_per_rental"
            ),
            CheckConstraint(
                condition=Q(unit_minutes__gt=0), name="item_duration_positive"
            ),
            CheckConstraint(
                condition=Q(unit_price__gte=0), name="item_price_nonegative"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.console} in rental {self.rental_id}"

    @property
    def units(self) -> int:
        """
        Number of pricing units to charge, round up, minimum 1
        """
        return max(1, math.ceil(self.rental.duration_minutes / self.unit_minutes))

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.units

    def clean(self) -> None:
        super().clean()
        existing_item = (
            self.pk is not None
            and RentalItem.objects.filter(
                pk=self.pk, console_id=self.console_id, rental_id=self.rental_id
            ).exists()
        )
        if self.pricing and self.pricing.console_id != self.console_id:
            raise ValidationError("pricing: This price belongs to another console")

        if self.pricing and not self.pricing.is_active and not existing_item:
            raise ValidationError("pricing: This pricing is not active")

        if not existing_item and self.console.status != Console.Status.AVAILABLE:
            raise ValidationError("console: This console is not available")

        if not self.console.is_free_between(
            self.rental.start_at, self.rental.end_at, exclude_rental=self.rental
        ):
            raise ValidationError("console: This console is not available")
