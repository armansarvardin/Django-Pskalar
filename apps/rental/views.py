from typing import Any

from django.db import OperationalError
from django.db.models import QuerySet
from rest_framework import generics, status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.rental.models import Console, ConsolePrice, Rental
from apps.rental.serializers import (
    ConsolePriceSerializer,
    ConsoleSerializer,
    PriceFilterSerializer,
    RentalCreateSerializer,
    RentalSerializer,
)


class AuthenticatedAPIView(generics.GenericAPIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]


class ConsoleListView(AuthenticatedAPIView, generics.ListAPIView):
    queryset = Console.objects.filter(deleted_at__isnull=True)
    serializer_class = ConsoleSerializer


class ConsolePriceListView(AuthenticatedAPIView, generics.ListAPIView):
    serializer_class = ConsolePriceSerializer

    def get_queryset(self) -> QuerySet[ConsolePrice]:
        filters = PriceFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return ConsolePrice.objects.filter(
            deleted_at__isnull=True,
            console__deleted_at__isnull=True,
            is_active=True,
            **filters.validated_data,
        )


class RentalQuerysetView(AuthenticatedAPIView):
    serializer_class = RentalSerializer

    def get_queryset(self) -> QuerySet[Rental]:
        rentals = Rental.objects.filter(deleted_at__isnull=True).prefetch_related(
            "items"
        )
        if not self.request.user.is_staff:
            rentals = rentals.filter(customer=self.request.user)
        return rentals


class RentalListCreateView(RentalQuerysetView, generics.ListCreateAPIView):
    def get_serializer_class(self) -> type:
        if self.request.method == "POST":
            return RentalCreateSerializer
        return RentalSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rental = serializer.save()
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            return Response(
                {"detail": "The database id busy, please retry"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(RentalSerializer(rental).data, status=status.HTTP_201_CREATED)


class RentalDetailView(RentalQuerysetView, generics.RetrieveAPIView):
    pass
