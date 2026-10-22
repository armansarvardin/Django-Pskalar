from django.contrib import admin

from django.contrib.admin import ModelAdmin, TabularInline, display, register
from apps.finance.models import DailyReport, Expense, Payment, PaymentMethod, Shift

from apps.finance.services import cash_difference, expected_cash

from apps.finance.forms import PaymentAdminForm
from apps.finance.services import cash_difference, expected_cash, prepare_payment

class SoftDeleteAdmin(ModelAdmin):
    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

@register(PaymentMethod)
class PaymentMethodAdmin(SoftDeleteAdmin):
    list_display = ("id", "name", "code", "commission_percent", "requires_reference", "is_active")
    list_display_links = ("id", "name")
    list_editable = ("commission_percent", "is_active")
    list_filter = ("is_active", "requires_reference")
    search_fields = ("name", "code")
    readonly_fields = ("created_at", "updated_at", "deleted_at")

class PaymentInline(TabularInline):
    model = Payment
    form = PaymentAdminForm
    extra = 0
    fields = ("rental", "method", "amount", "commission_amount", "status", "external_ref", "paid_at")
    readonly_fields = ("commission_amount",)
    raw_id_fields = ("rental",)
    show_change_link = True

class ExpenseInline(TabularInline):
    model = Expense
    extra = 0
    fields = ("category", "amount", "paid_from_cash", "description")

@register(Shift)
class ShiftAdmin(SoftDeleteAdmin):
    list_display = ("id", "cashier", "status", "opened_at", "closed_at", "opening_cash", "closing")
    list_display_links = ("id", "cashier")
    list_filter = ("status", "cashier")
    search_fields = ("cashier__username",)
    date_hierarchy = "opened_at"
    inlines = (PaymentInline, ExpenseInline)
    readonly_fields = (
        "opened_at",
        "show_expected_cash",
        "show_cash_difference",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    fieldsets = (
        ("Shift", {"fields": ("cashier", "status", ("opened_at", "closed_at"))}),
        ("Cash", {"fields": ("opening_cash", "closing", "show_expected_cash", "show_cash_difference")}),
        ("Dates", {"fields": ("created_at", "updated_at", "deleted_at"), "classes":("collapse",)}),
    )

    @display(description="Expected cash")
    def show_expected_cash(self, obj):
        if obj.pk is None:
            return "-"
        return expected_cash(obj)

    @display(description="Cash difference")
    def show_cash_difference(self, obj):
        if obj.pk is None:
            return "-"
        diff = cash_difference(obj)
        return "-" if diff is None else diff

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, Payment):
                prepare_payment(obj)
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()


@register(Payment)
class PaymentAdmin(SoftDeleteAdmin):
    form = PaymentAdminForm
    list_display = ("id", "rental", "method", "amount", "commission_amount", "status", "paid_at", "shift")
    list_display_links = ("id", "rental")
    search_fields = ("external_ref",)
    date_hierarchy = "paid_at"
    raw_id_fields = ("rental", "shift")
    readonly_fields = ("commission_amount", "paid_at", "created_at", "updated_at", "deleted_at")

    def save_model(self, request, obj, form, change):
        prepare_payment(obj)
        super().save_model(request, obj, form, change)


@register(Expense)
class ExpenseAdmin(SoftDeleteAdmin):
    list_display = ("id", "category", "amount", "paid_from_cash", "shift", "created_at")
    list_filter = ("category", "paid_from_cash", "created_at")
    search_fields = ("description",)
    date_hierarchy = "created_at"
    raw_id_fields = ("shift",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")


@register(DailyReport)
class DailyReportAdmin(SoftDeleteAdmin):
    list_display = ("date", "rentals_count", "gross_income", "commission_total", "expenses_total", "net_profit")
    date_hierarchy = "date"
    ordering = ("-date",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj = None):
        return False