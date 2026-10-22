from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.rental.models import Console, ConsolePrice, Rental, RentalItem


class ConsoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Console
        fields = (
            "id",
            "name",
            "platform",
            "serial_number",
            "status",
            "deposit",
            "gamepads_included",
        )


class ConsolePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsolePrice
        fields = ("id", "console", "name", "duration_minutes", "price", "is_active")


class PriceFilterSerializer(serializers.Serializer):
    console = serializers.IntegerField(min_value=1, required=False)


class RentalItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    class Meta:
        model = RentalItem
        fields = ("id", "console", "pricing", "unit_minutes", "unit_price", "subtotal")


class RentalSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )

    def get_items(self, rental: Rental) -> list[dict[str, Any]]:
        items = [item for item in rental.items.all() if item.deleted_at is None]
        return RentalItemSerializer(items, many=True).data

    class Meta:
        model = Rental
        fields = (
            "id",
            "customer",
            "status",
            "start_at",
            "end_at",
            "returned_at",
            "delivery_address",
            "deposit_amount",
            "notes",
            "items",
            "total_price",
        )


class RentalItemInputSerializer(serializers.Serializer):
    console = serializers.PrimaryKeyRelatedField(
        queryset=Console.objects.filter(deleted_at__isnull=True)
    )
    pricing = serializers.PrimaryKeyRelatedField(
        queryset=ConsolePrice.objects.filter(deleted_at__isnull=True, is_active=True)
    )


class RentalCreateSerializer(serializers.Serializer):
    end_at = serializers.DateTimeField()
    items = RentalItemInputSerializer(many=True, allow_empty=False)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_end_at(self, value: datetime) -> datetime:
        if value <= timezone.now():
            raise serializers.ValidationError("End date must be in the future")
        return value

    def validate_items(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        console_ids = [item["console"].pk for item in value]
        if len(console_ids) != len(set(console_ids)):
            raise serializers.ValidationError("A console can only be included once")

        for item in value:
            if item["pricing"].console_id != item["console"].pk:
                raise serializers.ValidationError(
                    "The tariff belongs to another console"
                )
        return value

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Rental:
        items = validated_data.pop("items")
        start_at = timezone.now()
        end_at = validated_data["end_at"]
        if end_at <= start_at:
            raise serializers.ValidationError(
                {"end_at": "End date must be in the future"}
            )

        reserved = []
        for item in sorted(items, key=lambda item: item["console"].pk):
            console_id = item["console"].pk
            updated = Console.objects.filter(
                pk=console_id, status=Console.Status.AVAILABLE, deleted_at__isnull=True
            ).update(status=Console.Status.TAKEN, updated_at=start_at)
            if updated != 1:
                raise serializers.ValidationError(
                    {"items": "A console is not available"}
                )

            console = Console.objects.get(pk=console_id)
            has_active_rental = RentalItem.objects.filter(
                console=console,
                deleted_at__isnull=True,
                rental__deleted_at__isnull=True,
                rental__status=Rental.Status.ACTIVE,
            ).exists()
            if has_active_rental or not console.is_free_between(start_at, end_at):
                raise serializers.ValidationError(
                    {"items": "A console is already booked"}
                )

            pricing = (
                ConsolePrice.objects.select_for_update()
                .filter(
                    pk=item["pricing"].pk,
                    console=console,
                    is_active=True,
                    deleted_at__isnull=True,
                )
                .first()
            )
            if pricing is None or pricing.duration_minutes <= 0 or pricing.price < 0:
                raise serializers.ValidationError(
                    {"items": "The tariff is not available"}
                )
            reserved.append((console, pricing))

        deposit = sum((console.deposit for console, _ in reserved), Decimal("0"))
        if deposit < 0 or deposit > Decimal("99999999.99"):
            raise serializers.ValidationError({"items": "The total deposit is invalid"})

        rental = Rental.objects.create(
            customer=self.context["request"].user,
            start_at=start_at,
            status=Rental.Status.ACTIVE,
            deposit_amount=deposit,
            **validated_data,
        )
        for console, pricing in reserved:
            RentalItem.objects.create(
                rental=rental,
                console=console,
                pricing=pricing,
                unit_minutes=pricing.duration_minutes,
                unit_price=pricing.price,
            )
        return rental
