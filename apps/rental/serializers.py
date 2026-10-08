from rest_framework import serializers

from apps.rental.models import Console, ConsolePrice, Rental, RentalItem


class ConsolePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsolePrice
        fields = [
            'id', 'console', 'name', 'duration_minutes', 'price',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConsoleSerializer(serializers.ModelSerializer):
    prices = ConsolePriceSerializer(many=True, read_only=True)

    class Meta:
        model = Console
        fields = [
            'id', 'name', 'platform', 'serial_number', 'status',
            'deposit', 'gamepads_included', 'notes',
            'prices', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RentalItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalItem
        fields = [
            'id', 'rental', 'console', 'pricing',
            'unit_minutes', 'unit_price', 'returned_at',
            'condition_notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RentalSerializer(serializers.ModelSerializer):
    items = RentalItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )

    class Meta:
        model = Rental
        fields = [
            'id', 'customer', 'status', 'start_at', 'end_at',
            'returned_at', 'delivery_address', 'deposit_amount',
            'notes', 'items', 'total_price',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
