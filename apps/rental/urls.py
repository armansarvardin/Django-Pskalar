from django.urls import path

from apps.rental.views import (
    ConsoleListView,
    ConsolePriceListView,
    RentalDetailView,
    RentalListCreateView,
)

app_name = "rental"

urlpatterns = [
    path("consoles/", ConsoleListView.as_view(), name="console-list"),
    path("prices/", ConsolePriceListView.as_view(), name="price-list"),
    path("rentals/", RentalListCreateView.as_view(), name="rental-list"),
    path("rentals/<int:pk>/", RentalDetailView.as_view(), name="rental-detail"),
]
