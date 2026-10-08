from rest_framework import viewsets, permissions

from apps.rental.models import Console, ConsolePrice, Rental, RentalItem
from apps.rental.serializers import (
    ConsoleSerializer,
    ConsolePriceSerializer,
    RentalSerializer,
    RentalItemSerializer,
)


class ConsoleViewSet(viewsets.ModelViewSet):
    queryset = Console.objects.filter(deleted_at__isnull=True)
    serializer_class = ConsoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class ConsolePriceViewSet(viewsets.ModelViewSet):
    queryset = ConsolePrice.objects.filter(deleted_at__isnull=True)
    serializer_class = ConsolePriceSerializer
    permission_classes = [permissions.IsAuthenticated]


class RentalViewSet(viewsets.ModelViewSet):
    queryset = Rental.objects.filter(deleted_at__isnull=True).prefetch_related('items')
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]


class RentalItemViewSet(viewsets.ModelViewSet):
    queryset = RentalItem.objects.filter(deleted_at__isnull=True)
    serializer_class = RentalItemSerializer
    permission_classes = [permissions.IsAuthenticated]
