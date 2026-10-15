from decimal import Decimal
from enum import unique

from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.db.models.enums import TextChoices
from django.db.models.fields import IntegerField, CharField, DecimalField, PositiveIntegerField, TextField, BooleanField
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

    class Meta:
        ordering = ['platform', 'name']

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
    )

    status = CharField(max_length=25, choices=Status.choices, default=Status.PENDING)