from decimal import Decimal

from django.conf import settings
from django.db.models import (
    CASCADE,
    PROTECT,
    BooleanField,
    CharField,
    CheckConstraint,
    DecimalField,
    ForeignKey,
    Index,
    PositiveIntegerField,
    Q,
    TextChoices,
    TextField,
    UniqueConstraint,
)

from apps.abstracts.models import AbstractBaseModel


class Category(AbstractBaseModel):
    """Group of products, e.g. Drinks or Snacks."""

    NAME_MAX_LEN = 50

    name = CharField(
        max_length=NAME_MAX_LEN,
        verbose_name="name",
    )

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ("name",)
        constraints = [
            UniqueConstraint(
                fields=("name",),
                condition=Q(deleted_at__isnull=True),
                name="unique_active_category_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Product(AbstractBaseModel):
    """One item the store sells, e.g. Coca-Cola 0.5 L."""

    NAME_MAX_LEN = 100
    SKU_MAX_LEN = 30
    LOW_STOCK_LIMIT = 5

    category = ForeignKey(
        to=Category,
        on_delete=PROTECT,
        related_name="products",
        verbose_name="category",
    )
    name = CharField(
        max_length=NAME_MAX_LEN,
        verbose_name="name",
    )
    sku = CharField(
        max_length=SKU_MAX_LEN,
        verbose_name="SKU",
        help_text="Unique product code, e.g. DRK-COLA-05",
    )
    description = TextField(
        blank=True,
        default="",
        verbose_name="description",
    )
    price = DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="price",
    )
    stock = PositiveIntegerField(
        default=0,
        verbose_name="in stock",
    )
    is_active = BooleanField(
        default=True,
        verbose_name="is on sale",
    )

    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        ordering = ("category__name", "name")
        constraints = [
            UniqueConstraint(
                fields=("sku",),
                condition=Q(deleted_at__isnull=True),
                name="unique_active_product_sku",
            ),
            CheckConstraint(
                condition=Q(price__gte=0),
                name="product_price_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self) -> bool:
        return self.stock <= self.LOW_STOCK_LIMIT


class Sale(AbstractBaseModel):
    """One purchase at the store counter."""

    STATUS_MAX_LEN = 10

    class Status(TextChoices):
        COMPLETED = "COMPLETED", "Completed"
        CANCELED = "CANCELED", "Canceled"

    cashier = ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        related_name="store_sales",
        verbose_name="cashier",
    )
    customer = ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=PROTECT,
        null=True,
        blank=True,
        related_name="store_purchases",
        verbose_name="customer",
    )
    status = CharField(
        max_length=STATUS_MAX_LEN,
        choices=Status,
        default=Status.COMPLETED,
        verbose_name="status",
    )
    note = TextField(
        blank=True,
        default="",
        verbose_name="note",
    )

    class Meta:
        verbose_name = "sale"
        verbose_name_plural = "sales"
        ordering = ("-created_at",)
        get_latest_by = "created_at"
        indexes = [
            Index(
                fields=("status", "created_at"),
                name="sale_status_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Sale #{self.pk}"

    @property
    def total(self) -> Decimal:
        return sum(
            (item.subtotal for item in self.items.all()),
            Decimal("0"),
        )


class SaleItem(AbstractBaseModel):
    """One product line inside a sale, e.g. 2 x Coca-Cola."""

    sale = ForeignKey(
        to=Sale,
        on_delete=CASCADE,
        related_name="items",
        verbose_name="sale",
    )
    product = ForeignKey(
        to=Product,
        on_delete=PROTECT,
        related_name="sale_items",
        verbose_name="product",
    )
    quantity = PositiveIntegerField(
        default=1,
        verbose_name="quantity",
    )
    unit_price = DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="price per item",
        help_text="Price for one item at the moment of sale.",
    )

    class Meta:
        verbose_name = "sale item"
        verbose_name_plural = "sale items"
        ordering = ("id",)
        constraints = [
            UniqueConstraint(
                fields=("sale", "product"),
                condition=Q(deleted_at__isnull=True),
                name="unique_active_sale_product",
            ),
            CheckConstraint(
                condition=Q(quantity__gt=0),
                name="sale_item_quantity_positive",
            ),
            CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="sale_item_price_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self) -> Decimal:
        return self.quantity * self.unit_price