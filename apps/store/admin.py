from decimal import Decimal

from django.contrib.admin import ModelAdmin, TabularInline, display, register
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from apps.store.filters import LowStockFilter
from apps.store.models import Category, Product, Sale, SaleItem


class StoreBaseAdmin(ModelAdmin):

    def has_delete_permission(
            self, 
            request: HttpRequest, 
            obj: object = None,
        ) -> bool:
        if obj is None:
            return False
        return super().has_delete_permission(request, obj)

@register(Category)
class CategoryAdmin(StoreBaseAdmin):
    list_display = ("id", "name", "products_count", "created_at")
    list_display_links = ("id", "name")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")

    @display(description="Products")
    def products_count(self, obj: Category) -> int:
        return obj.products.count()

@register(Product)
class ProductAdmin(StoreBaseAdmin):

    list_display = (
        "id",
        "name",
        "sku",
        "category",
        "price",
        "stock",
        "stock_status",
        "is_active",
    )
    list_display_links = ("id", "name")
    list_editable = ("price", "stock", "is_active")
    list_filter = ("category", "is_active", LowStockFilter)
    search_fields = ("name", "=sku")
    search_help_text = "Search by name or exact SKU"
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    fieldsets = (
        ("Product", {"fields": ("category", "name", "sku", "description")}),
        ("Price and stock", {"fields": ("price", "stock", "is_active")}),
        (
            "Dates",
            {
                "fields": ("created_at", "updated_at", "deleted_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Stock status")
    def stock_status(self, obj: Product) -> str:
        if obj.is_low_stock:
            return mark_safe('<b style="color: red;">Low</b>')
        return mark_safe('<b style="color: green;">OK</b>')


class SaleItemInline(TabularInline):
    model = SaleItem
    extra = 1
    fields = ("product", "quantity", "unit_price", "show_subtotal")
    readonly_fields = ("show_subtotal",)

    @display(description="Subtotal")
    def show_subtotal(self, obj: SaleItem) -> Decimal | str:
        if obj.unit_price is None:
            return "-"
        return obj.subtotal

@register(Sale)
class SaleAdmin(StoreBaseAdmin):

    list_display = (
        "id",
        "created_at",
        "cashier",
        "customer",
        "items_count",
        "show_total",
        "status",
    )
    list_display_links = ("id", "created_at")
    search_fields = ("=id", "note")
    date_hierarchy = "created_at"
    inlines = (SaleItemInline,)
    readonly_fields = ("show_total", "created_at", "updated_at", "deleted_at")
    fieldsets = (
        ("Sale", {"fields": ("cashier", "customer", "status", "show_total", "note")}),
        (
            "Dates",
            {
                "fields": ("created_at", "updated_at", "deleted_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Items")
    def items_count(self, obj: Sale) -> int:
        return obj.items.count()

    @display(description="Total")
    def show_total(self, obj: Sale) -> Decimal | str:
        if obj.pk is None:
            return "-"
        return obj.total