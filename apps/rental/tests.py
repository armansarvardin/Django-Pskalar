from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.test import APITestCase

from apps.rental.models import Console, ConsolePrice, Rental, RentalItem


class RentalAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        user_model = get_user_model()
        cls.customer = user_model.objects.create_user(username="customer")
        cls.other = user_model.objects.create_user(username="other")
        cls.staff = user_model.objects.create_user(username="staff", is_staff=True)

    def setUp(self) -> None:
        self.now = datetime(2026, 10, 18, 10, tzinfo=UTC)
        clock = patch("django.utils.timezone.now", return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.client.force_authenticate(self.customer)
        self.console = Console.objects.create(
            name="PS5 One",
            platform=Console.Platform.PS5,
            serial_number="PS5-001",
            deposit=Decimal("5000.00"),
        )
        self.second = Console.objects.create(
            name="PS5 Two",
            platform=Console.Platform.PS5,
            serial_number="PS5-002",
            deposit=Decimal("3000.00"),
        )
        self.price = ConsolePrice.objects.create(
            console=self.console,
            name="Hourly",
            duration_minutes=60,
            price=Decimal("1000.00"),
        )
        self.second_price = ConsolePrice.objects.create(
            console=self.second,
            name="Hourly",
            duration_minutes=60,
            price=Decimal("1500.00"),
        )

    def payload(self, **changes: Any) -> dict[str, Any]:
        data = {
            "end_at": (self.now + timedelta(hours=2)).isoformat(),
            "items": [{"console": self.console.pk, "pricing": self.price.pk}],
        }
        data.update(changes)
        return data

    def create_rental(self, **changes: Any) -> Rental:
        data = {
            "customer": self.customer,
            "status": Rental.Status.PENDING,
            "start_at": self.now - timedelta(hours=1),
            "end_at": self.now + timedelta(hours=1),
            "returned_at": None,
        }

        data.update(changes)
        return Rental.objects.create(**data)

    def add_booking(self, **changes: Any) -> Rental:
        rental = self.create_rental(**changes)
        RentalItem.objects.create(
            rental=rental,
            console=self.console,
            pricing=self.price,
            unit_minutes=60,
            unit_price=Decimal("1000.00"),
        )
        return rental

    def assert_rejected(self, payload: dict[str, Any]) -> Response:
        counts = (Rental.objects.count(), RentalItem.objects.count())
        statuses = dict(Console.objects.values_list("pk", "status"))
        response = self.client.post("/api/rentals/", payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(counts, (Rental.objects.count(), RentalItem.objects.count()))
        self.assertEqual(statuses, dict(Console.objects.values_list("pk", "status")))
        return response

    def test_anonymous_requests_require_authentication(self) -> None:
        rental = self.create_rental()
        self.client.force_authenticate(None)
        for url in (
            "/api/consoles/",
            "/api/prices/",
            "/api/rentals/",
            f"/api/rentals/{rental.pk}/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)
        response = self.client.post("/api/rentals/", self.payload(), format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Rental.objects.count(), 1)
        self.assertEqual(RentalItem.objects.count(), 0)

    def test_client_cannot_set_owner_status_times_or_prices(self) -> None:
        payload = self.payload(
            customer=self.other.pk,
            status=Rental.Status.COMPLETED,
            start_at=(self.now - timedelta(days=1)).isoformat(),
            returned_at=self.now.isoformat(),
            deposit_amount="0",
            total_price="0",
        )
        payload["items"][0].update(unit_minutes=1, unit_price="0")
        response = self.client.post("/api/rentals/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        rental = Rental.objects.get()
        item = rental.items.get()
        self.assertEqual(rental.customer_id, self.customer.pk)
        self.assertEqual(rental.status, Rental.Status.ACTIVE)
        self.assertEqual(rental.start_at, self.now)
        self.assertIsNone(rental.returned_at)
        self.assertEqual((item.unit_minutes, item.unit_price), (60, Decimal("1000.00")))
        self.assertEqual(rental.deposit_amount, Decimal("5000.00"))

    def test_list_is_own_only_unless_staff(self) -> None:
        own = self.create_rental()
        other = self.create_rental(customer=self.other)
        response = self.client.get("/api/rentals/")
        self.assertEqual([row["id"] for row in response.data], [own.pk])
        self.client.force_authenticate(self.staff)
        response = self.client.get("/api/rentals/")
        self.assertEqual({row["id"] for row in response.data}, {own.pk, other.pk})

    def test_other_customer_detail_is_hidden_but_staff_can_read_it(self) -> None:
        rental = self.create_rental(customer=self.other)
        url = f"/api/rentals/{rental.pk}/"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_missing_invalid_or_past_end_is_rejected(self) -> None:
        for value in (
            None,
            "not-a-date",
            self.now.isoformat(),
            (self.now - timedelta(seconds=1)).isoformat(),
        ):
            with self.subTest(end_at=value):
                self.assert_rejected(self.payload(end_at=value))
        payload = self.payload()
        del payload["end_at"]
        self.assert_rejected(payload)

    def test_empty_missing_or_duplicate_items_are_rejected(self) -> None:
        item = {"console": self.console.pk, "pricing": self.price.pk}
        for items in ([], None, [item, item], [{}]):
            with self.subTest(items=items):
                self.assert_rejected(self.payload(items=items))
        payload = self.payload()
        del payload["items"]
        self.assert_rejected(payload)

    def test_later_invalid_console_rolls_back_first_console_and_all_rows(self) -> None:
        Console.objects.filter(pk=self.second.pk).update(
            status=Console.Status.MAINTENANCE,
        )
        payload = self.payload()
        payload["items"].append(
            {"console": self.second.pk, "pricing": self.second_price.pk}
        )
        self.assert_rejected(payload)

    def test_start_and_rounding(self) -> None:
        payload = self.payload(end_at=(self.now + timedelta(minutes=61)).isoformat())
        response = self.client.post("/api/rentals/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        rental = Rental.objects.get()
        self.console.refresh_from_db()
        self.assertEqual(rental.customer_id, self.customer.pk)
        self.assertEqual(rental.status, Rental.Status.ACTIVE)
        self.assertEqual(rental.start_at, self.now)
        self.assertIsNone(rental.returned_at)
        self.assertEqual(self.console.status, Console.Status.TAKEN)
        self.assertEqual(rental.deposit_amount, Decimal("5000.00"))
        self.assertEqual(Decimal(response.data["total_price"]), Decimal("2000.00"))
        item = rental.items.get()
        self.assertEqual((item.unit_minutes, item.unit_price), (60, Decimal("1000")))

    def test_second_start_is_rejected(self) -> None:
        response = self.client.post("/api/rentals/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assert_rejected(self.payload())
        self.assertEqual(Rental.objects.count(), 1)
        self.assertEqual(RentalItem.objects.count(), 1)

    def test_invalid_tariff_is_rejected(self) -> None:
        items = [{"console": self.console.pk, "pricing": self.second_price.pk}]
        self.assert_rejected(self.payload(items=items))
        ConsolePrice.objects.filter(pk=self.price.pk).update(is_active=False)
        self.assert_rejected(self.payload())

    def test_bookings_and_adjacent_boundary(self) -> None:
        cases = (
            (Rental.Status.PENDING, 30, 60),
            (Rental.Status.ACTIVE, -120, -1),
        )
        for status, start, end in cases:
            with self.subTest(status=status):
                booking = self.add_booking(
                    status=status,
                    start_at=self.now + timedelta(minutes=start),
                    end_at=self.now + timedelta(minutes=end),
                )
                self.assert_rejected(self.payload())
                Rental.objects.filter(pk=booking.pk).delete()
        self.add_booking(end_at=self.now)
        response = self.client.post("/api/rentals/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
