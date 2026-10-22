from rest_framework import serializers

from apps.finance.models import DailyReport, Expense, Payment, PaymentMethod, Shift
from apps.finance.services import cash_difference, expected_cash


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ("id", "code", "name", "commission_percent", "requires_reference", "is_active")


class ShiftSerializer(serializers.ModelSerializer):
    expected_cash = serializers.SerializerMethodField()
    cash_difference = serializers.SerializerMethodField()

    class Meta:
        model = Shift
        fields = (
            "id", "cashier", "status", "opened_at", "closed_at",
            "opening_cash", "closing", "expected_cash", "cash_difference",
        )

    def get_expected_cash(self, obj):
        return expected_cash(obj)

    def get_cash_difference(self, obj):
        return cash_difference(obj)


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id", "rental", "shift", "method", "amount", "commission_amount",
            "status", "external_ref", "paid_at", "created_at",
        )


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ("id", "shift", "category", "amount", "paid_from_cash", "description", "created_at")


class DailyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyReport
        fields = (
            "id", "date", "rentals_count", "gross_income", "cash_total", "kaspi_total",
            "card_total", "commission_total", "expenses_total", "net_profit", "generated_at",
        )


class DailyReportFilterSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)



class ShiftCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ("opening_cash",)

    def validate(self, attrs):
        if get_open_shift() is not None:
            raise serializers.ValidationError("A shift is already open. Close it first.")
        return attrs


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("rental", "method", "amount", "status", "external_ref")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be more than 0.")
        return value

    def validate_status(self, value):
        if value == Payment.Status.REFUNDED:
            raise serializers.ValidationError("Use the refund endpoint instead.")
        return value

    def validate(self, attrs):
        method = attrs["method"]
        if not method.is_active:
            raise serializers.ValidationError({"method": "This payment method is turned off."})
        if method.requires_reference and not attrs.get("external_ref"):
            raise serializers.ValidationError({"external_ref": "This payment method needs a transaction ID."})

        shift = get_open_shift()
        if shift is None:
            raise serializers.ValidationError("Open a shift before taking payments.")
        attrs["shift"] = shift

        rental = attrs["rental"]
        if paid_total(rental) + attrs["amount"] > rental.total_price:
            raise serializers.ValidationError({"amount": "This is more than what's left to pay for this rental."})
        return attrs

    def create(self, validated_data):
        payment = Payment(**validated_data)
        prepare_payment(payment)
        payment.save()
        return payment


class ExpenseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ("category", "amount", "paid_from_cash", "description")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be more than 0.")
        return value

    def validate(self, attrs):
        shift = get_open_shift()
        if attrs.get("paid_from_cash") and shift is None:
            raise serializers.ValidationError({"paid_from_cash": "Open a shift before paying from the cash drawer."})
        attrs["shift"] = shift
        return attrs



class ShiftCloseSerializer(serializers.Serializer):
    closing = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)


class PaymentRefundSerializer(serializers.Serializer):
    """No input needed, just send POST."""