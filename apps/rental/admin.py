from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from apps.rental.models import Console, ConsolePrice, Rental, RentalItem


class ConsolePriceInline(TabularInline):
    model = ConsolePrice
    extra = 1
    fields = ('name', 'duration_minutes', 'price', 'is_active')


@admin.register(Console)
class ConsoleAdmin(ModelAdmin):
    list_display = ('name', 'platform', 'serial_number', 'status', 'deposit', 'gamepads_included')
    list_filter = ('platform', 'status')
    search_fields = ('name', 'serial_number')
    ordering = ('platform', 'name')
    inlines = [ConsolePriceInline]


@admin.register(ConsolePrice)
class ConsolePriceAdmin(ModelAdmin):
    list_display = ('console', 'name', 'duration_minutes', 'price', 'is_active')
    list_filter = ('is_active', 'console__platform')
    search_fields = ('name', 'console__name')
    ordering = ('console', 'duration_minutes')


class RentalItemInline(TabularInline):
    model = RentalItem
    extra = 1
    fields = ('console', 'pricing', 'unit_minutes', 'unit_price', 'returned_at', 'condition_notes')


@admin.register(Rental)
class RentalAdmin(ModelAdmin):
    list_display = ('pk', 'customer', 'status', 'start_at', 'end_at', 'deposit_amount')
    list_filter = ('status',)
    search_fields = ('customer__username', 'customer__first_name', 'customer__last_name')
    ordering = ('-start_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RentalItemInline]


@admin.register(RentalItem)
class RentalItemAdmin(ModelAdmin):
    list_display = ('rental', 'console', 'pricing', 'unit_minutes', 'unit_price')
    list_filter = ('console__platform',)
    search_fields = ('console__name', 'rental__pk')
    readonly_fields = ('created_at', 'updated_at')
