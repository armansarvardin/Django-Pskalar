from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.store.models import Product

class LowStockFilter(SimpleListFilter):

    title = "stock level"
    parameter_name = "stock_level"

    LOW_KEY = "low"
    ENOUGH_KEY = "enough"

    def lookups(
            self, 
            request: HttpRequest, 
            model_admin: ModelAdmin,
        ) -> list[tuple[str, str]]:
        return [
            (self.LOW_KEY, "Low stock"),
            (self.ENOUGH_KEY, "Enough"),
        ]

    def queryset(
            self,
            request: HttpRequest, 
            queryset: QuerySet[Product]
        ):
        if self.value() == self.LOW_KEY:
            return queryset.filter(stock__lte=Product.LOW_STOCK_LIMIT)
        if self.value() == self.ENOUGH_KEY:
            return queryset.filter(stock__gt=Product.LOW_STOCK_LIMIT)
        return queryset.all()