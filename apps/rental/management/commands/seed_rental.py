import random
import string
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

from apps.auths.models import User
from apps.rental.models import Console, ConsolePrice, Rental, RentalItem


class Command(BaseCommand):
    """Fill the rental app with test consoles, price tiers and rentals."""

    help = "Create test consoles, price tiers and rentals."

    SERIAL_LEN = 10
    PS4_PRICE_RATE = Decimal("0.7")
    WALKIN_RATE = 0.2

    # name, platform, deposit, gamepads, status
    CONSOLES: list[tuple[str, str, str, int, str]] = [
        ("PS5 Digital Edition #1", Console.Platform.PS5, "200000.00", 2, Console.Status.AVAILABLE),
        ("PS5 Disc Edition #1", Console.Platform.PS5, "200000.00", 3, Console.Status.AVAILABLE),
        ("PS5 Slim #1", Console.Platform.PS5, "200000.00", 2, Console.Status.AVAILABLE),
        ("PS5 Slim #2", Console.Platform.PS5, "200000.00", 2, Console.Status.MAINTENANCE),
        ("PS4 Slim #1", Console.Platform.PS4, "100000.00", 2, Console.Status.AVAILABLE),
        ("PS4 Pro #1", Console.Platform.PS4, "100000.00", 2, Console.Status.AVAILABLE),
        ("PS4 Pro #2", Console.Platform.PS4, "100000.00", 2, Console.Status.RETIRED),
    ]
    # name, minutes, PS5 price
    PRICE_TIERS: list[tuple[str, int, str]] = [
        ("30 min", 30, "15000.00"),
        ("1 hour", 60, "25000.00"),
        ("2 hours", 120, "40000.00"),
        ("3 hours", 180, "55000.00"),
        ("Full day", 480, "120000.00"),
    ]
    STATUS_WEIGHTS: dict[str, int] = {
        Rental.Status.COMPLETED: 5,
        Rental.Status.ACTIVE: 2,
        Rental.Status.PENDING: 2,
        Rental.Status.CANCELED: 1,
    }
    WALKINS: list[tuple[str, str]] = [
        ("Bekzod", "+998901234567"),
        ("Sanjar", "+998937654321"),
        ("Asilbek", "+998946543210"),
        ("Nodir", ""),
    ]

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--rentals",
            type=int,
            default=10,
            help="How many new rentals to create on each run (default: 10)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Command entry point."""
        rentals_count: int = options["rentals"]
        if rentals_count < 0:
            raise CommandError("--rentals can't be negative")

        with transaction.atomic():
            consoles: list[Console] = self.__create_consoles()
            prices: list[ConsolePrice] = self.__create_prices()
            rentals: list[Rental] = self.__create_rentals(rentals_count)

        if consoles or prices or rentals:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {len(consoles)} consoles, {len(prices)} price tiers "
                    f"and {len(rentals)} rentals."
                )
            )
        else:
            self.stdout.write(self.style.WARNING("Nothing new to create."))

    def __create_consoles(self) -> list[Console]:
        """Create consoles that don't exist yet. Skip known names."""
        used_names: set[str] = set(
            Console.objects.filter(deleted_at__isnull=True).values_list("name", flat=True)
        )
        # Serial numbers are unique across soft-deleted consoles too.
        used_serials: set[str] = set(
            Console.objects.values_list("serial_number", flat=True)
        )

        new_consoles: list[Console] = []
        for name, platform, deposit, gamepads, status in self.CONSOLES:
            if name in used_names:
                continue
            used_names.add(name)
            new_consoles.append(
                Console(
                    name=name,
                    platform=platform,
                    serial_number=self.__new_serial(used_serials),
                    deposit=Decimal(deposit),
                    gamepads_included=gamepads,
                    status=status,
                )
            )

        Console.objects.bulk_create(new_consoles)
        return new_consoles

    def __new_serial(self, used_serials: set[str]) -> str:
        """Return a random serial number that isn't taken yet."""
        alphabet: str = string.ascii_uppercase + string.digits
        while True:
            serial: str = "SN-" + "".join(random.choices(alphabet, k=self.SERIAL_LEN))
            if serial not in used_serials:
                used_serials.add(serial)
                return serial

    def __create_prices(self) -> list[ConsolePrice]:
        """Give every console the missing price tiers. PS4 is cheaper."""
        # One tier per duration per console, soft-deleted ones included.
        used_tiers: set[tuple[int, int]] = set(
            ConsolePrice.objects.values_list("console_id", "duration_minutes")
        )

        new_prices: list[ConsolePrice] = []
        for console in Console.objects.filter(deleted_at__isnull=True):
            for name, minutes, price in self.PRICE_TIERS:
                if (console.pk, minutes) in used_tiers:
                    continue
                amount: Decimal = Decimal(price)
                if console.platform == Console.Platform.PS4:
                    amount = (amount * self.PS4_PRICE_RATE).quantize(Decimal("1"))
                new_prices.append(
                    ConsolePrice(
                        console=console,
                        name=name,
                        duration_minutes=minutes,
                        price=amount,
                    )
                )

        ConsolePrice.objects.bulk_create(new_prices)
        return new_prices

    def __create_rentals(self, count: int) -> list[Rental]:
        """Create rentals with one console each, spread over all statuses."""
        if count == 0:
            return []

        prices: list[ConsolePrice] = list(
            ConsolePrice.objects.filter(
                deleted_at__isnull=True,
                is_active=True,
                console__deleted_at__isnull=True,
                console__status=Console.Status.AVAILABLE,
            ).select_related("console")
        )
        if not prices:
            raise CommandError("No available consoles with prices to rent.")

        customers: list[User] = list(
            User.objects.filter(deleted_at__isnull=True, is_staff=False)
        )
        now: datetime = timezone.now()

        rentals: list[Rental] = []
        for _ in range(count):
            price: ConsolePrice = random.choice(prices)
            status: str = random.choices(
                list(self.STATUS_WEIGHTS),
                weights=list(self.STATUS_WEIGHTS.values()),
            )[0]
            start_at, end_at, returned_at = self.__get_period(
                status, price.duration_minutes, now
            )
            # Pending and active rentals block the console, so they can't overlap.
            if status in Rental.BLOCKING_STATUSES and not price.console.is_free_between(
                start_at, end_at
            ):
                status = Rental.Status.COMPLETED
                start_at, end_at, returned_at = self.__get_period(
                    status, price.duration_minutes, now
                )

            rental: Rental = Rental(
                status=status,
                start_at=start_at,
                end_at=end_at,
                returned_at=returned_at,
                deposit_amount=price.console.deposit,
            )
            if customers and random.random() >= self.WALKIN_RATE:
                rental.customer = random.choice(customers)
            else:
                rental.customer_name, rental.customer_phone = random.choice(self.WALKINS)
            rental.save()

            RentalItem.objects.create(
                rental=rental,
                console=price.console,
                pricing=price,
                unit_minutes=price.duration_minutes,
                unit_price=price.price,
                returned_at=returned_at,
            )
            rentals.append(rental)
        return rentals

    def __get_period(
        self,
        status: str,
        minutes: int,
        now: datetime,
    ) -> tuple[datetime, datetime, datetime | None]:
        """Return start, end and return time that make sense for the status."""
        returned_at: datetime | None = None
        if status == Rental.Status.COMPLETED:
            start_at = now - timedelta(days=random.randint(3, 30), hours=random.randint(0, 10))
            returned_at = start_at + timedelta(minutes=minutes + random.randint(-5, 15))
        elif status == Rental.Status.ACTIVE:
            start_at = now - timedelta(minutes=random.randint(1, minutes - 1))
        elif status == Rental.Status.PENDING:
            start_at = now + timedelta(days=random.randint(1, 7), hours=random.randint(0, 8))
        else:
            start_at = now - timedelta(days=random.randint(1, 10))
        return start_at, start_at + timedelta(minutes=minutes), returned_at
