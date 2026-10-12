import random
import string
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.auths.models import User
from apps.rental.models import Console, ConsolePrice, Rental, RentalItem
from apps.finance.models import Invoice, Payment

FIRST_NAMES = [
    'Arman', 'Daniyal', 'Sardor', 'Jasur', 'Aziz',
    'Nilufar', 'Madina', 'Kamila', 'Shakhzod', 'Bobur',
    'Timur', 'Otabek', 'Dilshod', 'Farrukh', 'Zarina',
]
LAST_NAMES = [
    'Sarvardin', 'Karimov', 'Aliev', 'Rakhimov', 'Umarov',
    'Nazarova', 'Kholmatova', 'Toshmatov', 'Mirzaev', 'Yusupov',
]
ADDRESSES = [
    'Tashkent, Yunusabad 4, Block 12',
    'Tashkent, Chilanzar 9, Apt 45',
    'Samarkand, Registan St 7',
    'Tashkent, Mirzo Ulugbek, Block 3',
    'Bukhara, Naqshbandi 15',
    'Tashkent, Sergeli, Yangi Hayot 22',
    'Namangan, Navoi 8',
    'Fergana, Mustaqillik 33',
]
CONSOLE_NAMES_PS5 = [
    'PS5 Digital Edition #1',
    'PS5 Disc Edition #1',
    'PS5 Slim #1',
    'PS5 Digital Edition #2',
    'PS5 Disc Edition #2',
    'PS5 Slim #2',
]
CONSOLE_NAMES_PS4 = [
    'PS4 Slim #1',
    'PS4 Pro #1',
    'PS4 Slim #2',
    'PS4 Pro #2',
]
PRICE_TIERS = [
    ('30 min', 30, Decimal('15000')),
    ('1 hour', 60, Decimal('25000')),
    ('2 hours', 120, Decimal('40000')),
    ('3 hours', 180, Decimal('55000')),
    ('Full day', 480, Decimal('120000')),
]
DELIVERY_ADDRESSES = [
    '',
    'Deliver to Mega Planet, 3rd floor',
    'Deliver to home: Yunusabad 7/2',
    'Pickup from office',
    '',
]
CONDITION_NOTES = [
    '',
    'Minor scratch on controller',
    'All good, returned clean',
    'One gamepad stick slightly loose',
    'HDMI cable missing on return',
    '',
]
PAYMENT_REFS = [
    'CLICK-{n}',
    'PAYME-{n}',
    'UZCARD-{n}',
    'CASH-{n}',
    'HUMO-{n}',
]


def random_serial():
    return 'SN-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


def random_phone():
    return f'+99890{random.randint(1000000, 9999999)}'


class Command(BaseCommand):
    help = 'Seed the database with realistic mock data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete all existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write('Flushing existing data...')
            Payment.objects.all().delete()
            Invoice.objects.all().delete()
            RentalItem.objects.all().delete()
            Rental.objects.all().delete()
            ConsolePrice.objects.all().delete()
            Console.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        now = timezone.now()

        # ── Users ────────────────────────────────────────
        self.stdout.write('Creating users...')
        users = []
        for i, (first, last) in enumerate(zip(FIRST_NAMES, LAST_NAMES)):
            username = f'{first.lower()}.{last.lower()}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'email': f'{username}@example.com',
                    'phone_number': random_phone(),
                    'address': random.choice(ADDRESSES),
                },
            )
            if created:
                user.set_password('testpass123')
                user.save()
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f'  {len(users)} users ready'))

        # ── Consoles ─────────────────────────────────────
        self.stdout.write('Creating consoles...')
        consoles = []
        for name in CONSOLE_NAMES_PS5:
            console, _ = Console.objects.get_or_create(
                name=name,
                defaults={
                    'platform': Console.Platform.PS5,
                    'serial_number': random_serial(),
                    'status': Console.Status.AVAILABLE,
                    'deposit': Decimal('200000'),
                    'gamepads_included': random.choice([2, 3]),
                },
            )
            consoles.append(console)

        for name in CONSOLE_NAMES_PS4:
            console, _ = Console.objects.get_or_create(
                name=name,
                defaults={
                    'platform': Console.Platform.PS4,
                    'serial_number': random_serial(),
                    'status': Console.Status.AVAILABLE,
                    'deposit': Decimal('100000'),
                    'gamepads_included': 2,
                },
            )
            consoles.append(console)

        # Put one in maintenance, one retired
        if len(consoles) >= 8:
            consoles[7].status = Console.Status.MAINTENANCE
            consoles[7].notes = 'HDMI port repair'
            consoles[7].save()
            consoles[9].status = Console.Status.RETIRED
            consoles[9].notes = 'Too old, donated'
            consoles[9].save()

        self.stdout.write(self.style.SUCCESS(f'  {len(consoles)} consoles ready'))

        # ── Console Prices ───────────────────────────────
        self.stdout.write('Creating price tiers...')
        prices_created = 0
        all_prices = {}  # console_id -> list of ConsolePrices
        for console in consoles:
            all_prices[console.pk] = []
            for tier_name, minutes, base_price in PRICE_TIERS:
                # PS4 is cheaper
                price = base_price if console.platform == Console.Platform.PS5 else base_price * Decimal('0.7')
                cp, created = ConsolePrice.objects.get_or_create(
                    console=console,
                    duration_minutes=minutes,
                    defaults={
                        'name': tier_name,
                        'price': price.quantize(Decimal('1')),
                    },
                )
                all_prices[console.pk].append(cp)
                if created:
                    prices_created += 1
        self.stdout.write(self.style.SUCCESS(f'  {prices_created} price tiers created'))

        # ── Rentals ──────────────────────────────────────
        self.stdout.write('Creating rentals...')
        available_consoles = [c for c in consoles if c.status == Console.Status.AVAILABLE]
        rentals = []

        # Past completed rentals
        for i in range(12):
            customer = random.choice(users)
            days_ago = random.randint(3, 30)
            start = now - timedelta(days=days_ago, hours=random.randint(10, 20))
            tier = random.choice(PRICE_TIERS)
            end = start + timedelta(minutes=tier[1])
            returned = end + timedelta(minutes=random.randint(-5, 15))

            rental = Rental.objects.create(
                customer=customer,
                status=Rental.Status.COMPLETED,
                start_at=start,
                end_at=end,
                returned_at=returned,
                delivery_address=random.choice(DELIVERY_ADDRESSES),
                deposit_amount=Decimal('100000'),
                notes=f'Completed rental #{i + 1}',
            )
            # 1-2 consoles per rental
            num_items = random.randint(1, 2)
            chosen = random.sample(available_consoles, min(num_items, len(available_consoles)))
            for console in chosen:
                cp = random.choice(all_prices[console.pk])
                RentalItem.objects.create(
                    rental=rental,
                    console=console,
                    pricing=cp,
                    unit_minutes=cp.duration_minutes,
                    unit_price=cp.price,
                    returned_at=returned,
                    condition_notes=random.choice(CONDITION_NOTES),
                )
            rentals.append(rental)

        # Active rentals (currently happening)
        for i in range(3):
            customer = random.choice(users)
            start = now - timedelta(hours=random.randint(1, 3))
            tier = random.choice(PRICE_TIERS[1:3])  # 1h or 2h
            end = start + timedelta(minutes=tier[1])

            rental = Rental.objects.create(
                customer=customer,
                status=Rental.Status.ACTIVE,
                start_at=start,
                end_at=end,
                deposit_amount=Decimal('150000'),
            )
            console = random.choice(available_consoles)
            cp = random.choice(all_prices[console.pk])
            RentalItem.objects.create(
                rental=rental,
                console=console,
                pricing=cp,
                unit_minutes=cp.duration_minutes,
                unit_price=cp.price,
            )
            rentals.append(rental)

        # Pending rentals (future bookings)
        for i in range(4):
            customer = random.choice(users)
            start = now + timedelta(days=random.randint(1, 7), hours=random.randint(10, 18))
            tier = random.choice(PRICE_TIERS)
            end = start + timedelta(minutes=tier[1])

            rental = Rental.objects.create(
                customer=customer,
                status=Rental.Status.PENDING,
                start_at=start,
                end_at=end,
                delivery_address=random.choice(DELIVERY_ADDRESSES),
                deposit_amount=Decimal('100000'),
            )
            console = random.choice(available_consoles)
            cp = random.choice(all_prices[console.pk])
            RentalItem.objects.create(
                rental=rental,
                console=console,
                pricing=cp,
                unit_minutes=cp.duration_minutes,
                unit_price=cp.price,
            )
            rentals.append(rental)

        # A couple canceled
        for i in range(2):
            customer = random.choice(users)
            start = now - timedelta(days=random.randint(1, 10))
            end = start + timedelta(hours=2)

            rental = Rental.objects.create(
                customer=customer,
                status=Rental.Status.CANCELED,
                start_at=start,
                end_at=end,
                notes='Customer canceled',
            )
            rentals.append(rental)

        self.stdout.write(self.style.SUCCESS(f'  {len(rentals)} rentals created'))

        # ── Invoices & Payments ──────────────────────────
        self.stdout.write('Creating invoices & payments...')
        invoices_created = 0
        payments_created = 0

        for rental in rentals:
            if rental.status == Rental.Status.CANCELED:
                continue

            total = rental.total_price
            if total <= 0:
                total = Decimal('25000')  # fallback for rentals without items

            if rental.status == Rental.Status.COMPLETED:
                inv_status = Invoice.Status.PAID
                issued = rental.start_at
                due = rental.end_at
            elif rental.status == Rental.Status.ACTIVE:
                inv_status = Invoice.Status.ISSUED
                issued = rental.start_at
                due = rental.end_at + timedelta(days=1)
            else:
                inv_status = Invoice.Status.DRAFT
                issued = None
                due = None

            invoice = Invoice.objects.create(
                rental=rental,
                customer=rental.customer,
                status=inv_status,
                total_amount=total,
                issued_at=issued,
                due_at=due,
            )
            invoices_created += 1

            # Completed → full payment; Active → partial; Pending → none
            if rental.status == Rental.Status.COMPLETED:
                ref_tpl = random.choice(PAYMENT_REFS)
                Payment.objects.create(
                    invoice=invoice,
                    amount=total,
                    method=random.choice([Payment.Method.CASH, Payment.Method.CARD, Payment.Method.TRANSFER]),
                    status=Payment.Status.COMPLETED,
                    reference=ref_tpl.format(n=random.randint(100000, 999999)),
                    paid_at=rental.returned_at or rental.end_at,
                )
                payments_created += 1
            elif rental.status == Rental.Status.ACTIVE:
                # Deposit payment
                deposit = rental.deposit_amount or Decimal('50000')
                ref_tpl = random.choice(PAYMENT_REFS)
                Payment.objects.create(
                    invoice=invoice,
                    amount=deposit,
                    method=random.choice([Payment.Method.CASH, Payment.Method.CARD]),
                    status=Payment.Status.COMPLETED,
                    reference=ref_tpl.format(n=random.randint(100000, 999999)),
                    paid_at=rental.start_at,
                )
                payments_created += 1

        self.stdout.write(self.style.SUCCESS(f'  {invoices_created} invoices, {payments_created} payments created'))

        # ── Summary ──────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Done! Database seeded:'))
        self.stdout.write(f'  Users:          {User.objects.filter(is_superuser=False).count()}')
        self.stdout.write(f'  Consoles:       {Console.objects.count()}')
        self.stdout.write(f'  Console Prices: {ConsolePrice.objects.count()}')
        self.stdout.write(f'  Rentals:        {Rental.objects.count()}')
        self.stdout.write(f'  Rental Items:   {RentalItem.objects.count()}')
        self.stdout.write(f'  Invoices:       {Invoice.objects.count()}')
        self.stdout.write(f'  Payments:       {Payment.objects.count()}')
