from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.finance.models import Invoice, Payment


class PaymentInline(TabularInline):
    model = Payment
    extra = 0
    fields = ('amount', 'method', 'status', 'reference', 'paid_at')
    readonly_fields = ('created_at',)


@admin.register(Invoice)
class InvoiceAdmin(ModelAdmin):
    list_display = ('pk', 'customer', 'rental', 'status', 'total_amount', 'issued_at', 'due_at')
    list_filter = ('status',)
    search_fields = ('customer__username', 'customer__first_name', 'customer__last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ('pk', 'invoice', 'amount', 'method', 'status', 'paid_at')
    list_filter = ('status', 'method')
    search_fields = ('reference', 'invoice__pk')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
