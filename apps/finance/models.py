from django.db import models
from django.conf import settings

from apps.abstracts.models import AbstractBaseModel

class PaymentMethod(AbstractBaseModel):

    class Code(models.TextChoices):

        CASH = "CASH", "Cash"
        KASPI_TRANSFER = "KASPI_TRANSFER", "Kaspi Transfer"
        KASPI_QR = "KASPI_QR", "Kaspi QR"
        CARD = "CARD", "Bank Card"

    code = models.CharField(
        max_length=20,
        choices=Code.choices,
        unique=True
    )

    name = models.CharField(max_length=50)

    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2, 
        default=0
    )

    requires_reference = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Shift(AbstractBaseModel):

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
    
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shifts"
    )

    opened_at = models.DateTimeField(
        auto_now_add=True,
    )
    
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    opening_cash = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    closing = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )    

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    def __str__(self):
        return f"shift #{self.pk} - {self.status}"

class Payment(AbstractBaseModel):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        REFUNDED = "REFUNDED", "Refunded"

    rental = models.ForeignKey(
        "rental.Rental",
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
    )
    sale = models.ForeignKey(
        "store.Sale",
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
        )

    shift = models.ForeignKey(
        "finance.Shift",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
    )

    method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits = 10,
        decimal_places=2,
    )

    commission_amount = models.DecimalField(
        max_digits = 10,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length = 10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    external_ref = models.CharField(
        max_length=64,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(rental__isnull=False, sale__isnull=True)
                    | models.Q(rental__isnull=True, sale__isnull=False)
                ),
                name = "payments_for_rental_or_sale",
            ),
        ]

    def __str__(self):
        return f"Payment #{self.pk} - {self.amount} tenge"

class Expense(AbstractBaseModel):

    class Category(models.TextChoices):
        RENT = "RENT", "Rent"
        SALARY = "SALARY", "Salary"
        UTILITIES = "UTILITIES", "Utilities"
        SUPPLIES = "SUPPLIES", "Supplies"
        REPAIR = "REPAIR", "Repair"
        OTHER = "OTHER", "Other"
    
    shift = models.ForeignKey(
        "finance.Shift",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expenses",
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    paid_from_cash = models.BooleanField(
        default=False,
    )

    description = models.CharField(
        max_length=200,
    )

    def __str__(self):
        return f"{self.get_category_display()} - {self.amount} tenge"

class DailyReport(AbstractBaseModel):

    date = models.DateField(
        unique=True,
    )

    rentals_count = models.PositiveIntegerField(
        default=0,
    )

    gross_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    cash_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    kaspi_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    card_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    commission_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    expenses_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    net_profit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    generated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Daily Report - {self.date}"

