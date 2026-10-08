from rest_framework import viewsets, permissions

from apps.finance.models import Invoice, Payment
from apps.finance.serializers import InvoiceSerializer, PaymentSerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.filter(deleted_at__isnull=True).prefetch_related('payments')
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.filter(deleted_at__isnull=True)
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
