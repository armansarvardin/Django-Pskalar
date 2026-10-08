from rest_framework.routers import DefaultRouter

from apps.rental.views import (
    ConsoleViewSet,
    ConsolePriceViewSet,
    RentalViewSet,
    RentalItemViewSet,
)

router = DefaultRouter()
router.register(r'consoles', ConsoleViewSet)
router.register(r'console-prices', ConsolePriceViewSet)
router.register(r'rentals', RentalViewSet)
router.register(r'rental-items', RentalItemViewSet)

urlpatterns = router.urls
