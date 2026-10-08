from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.rental.models import Console, ConsolePrice, Rental, RentalItem

User = get_user_model()


class ConsoleModelTests(TestCase):
    def test_create_console(self):
        console = Console.objects.create(
            name='PS5 Unit 1',
            platform=Console.Platform.PS5,
            serial_number='SN-001',
        )
        self.assertEqual(console.status, Console.Status.AVAILABLE)
        self.assertEqual(console.gamepads_included, 2)

    def test_console_str(self):
        console = Console.objects.create(
            name='PS5 Unit 1',
            platform=Console.Platform.PS5,
            serial_number='SN-002',
        )
        self.assertEqual(str(console), 'PS5 Unit 1 (PlayStation 5)')

    def test_serial_number_unique(self):
        Console.objects.create(
            name='A', platform=Console.Platform.PS4, serial_number='SN-DUP',
        )
        with self.assertRaises(Exception):
            Console.objects.create(
                name='B', platform=Console.Platform.PS4, serial_number='SN-DUP',
            )

    def test_soft_delete(self):
        console = Console.objects.create(
            name='Del', platform=Console.Platform.PS4, serial_number='SN-DEL',
        )
        console.delete()
        console.refresh_from_db()
        self.assertIsNotNone(console.deleted_at)


class ConsolePriceTests(TestCase):
    def setUp(self):
        self.console = Console.objects.create(
            name='PS5', platform=Console.Platform.PS5, serial_number='SN-100',
        )

    def test_create_price(self):
        price = ConsolePrice.objects.create(
            console=self.console, name='1 Hour',
            duration_minutes=60, price=Decimal('10.00'),
        )
        self.assertTrue(price.is_active)

    def test_price_str(self):
        price = ConsolePrice.objects.create(
            console=self.console, name='1 Hour',
            duration_minutes=60, price=Decimal('10.00'),
        )
        self.assertEqual(str(price), 'PS5 = 1 Hour: 10.00')


class RentalModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='renter', password='pass')
        self.console = Console.objects.create(
            name='PS5', platform=Console.Platform.PS5, serial_number='SN-200',
        )
        self.now = timezone.now()

    def test_create_rental(self):
        rental = Rental.objects.create(
            customer=self.user,
            start_at=self.now,
            end_at=self.now + timedelta(hours=2),
        )
        self.assertEqual(rental.status, Rental.Status.PENDING)

    def test_rental_str(self):
        rental = Rental.objects.create(
            customer=self.user,
            start_at=self.now,
            end_at=self.now + timedelta(hours=2),
        )
        self.assertIn(str(rental.pk), str(rental))

    def test_rental_clean_invalid_dates(self):
        rental = Rental(
            customer=self.user,
            start_at=self.now + timedelta(hours=2),
            end_at=self.now,
        )
        with self.assertRaises(ValidationError):
            rental.clean()

    def test_duration_minutes(self):
        rental = Rental.objects.create(
            customer=self.user,
            start_at=self.now,
            end_at=self.now + timedelta(hours=2),
        )
        self.assertAlmostEqual(rental.duration_minutes, 120.0, places=1)

    def test_total_price_empty(self):
        rental = Rental.objects.create(
            customer=self.user,
            start_at=self.now,
            end_at=self.now + timedelta(hours=2),
        )
        self.assertEqual(rental.total_price, Decimal('0'))


class RentalAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='admin123',
        )
        self.client.force_login(self.superuser)

    def test_console_changelist(self):
        response = self.client.get('/admin/rental/console/')
        self.assertEqual(response.status_code, 200)

    def test_rental_changelist(self):
        response = self.client.get('/admin/rental/rental/')
        self.assertEqual(response.status_code, 200)

    def test_consoleprice_changelist(self):
        response = self.client.get('/admin/rental/consoleprice/')
        self.assertEqual(response.status_code, 200)

    def test_rentalitem_changelist(self):
        response = self.client.get('/admin/rental/rentalitem/')
        self.assertEqual(response.status_code, 200)


class RentalAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='pass')
        self.client.force_login(self.user)

    def test_list_consoles(self):
        response = self.client.get('/api/v1/rental/consoles/')
        self.assertEqual(response.status_code, 200)

    def test_create_console(self):
        response = self.client.post('/api/v1/rental/consoles/', {
            'name': 'PS5 Test',
            'platform': Console.Platform.PS5,
            'serial_number': 'SN-API-001',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Console.objects.count(), 1)

    def test_list_rentals(self):
        response = self.client.get('/api/v1/rental/rentals/')
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_access_denied(self):
        self.client.logout()
        response = self.client.get('/api/v1/rental/consoles/')
        self.assertEqual(response.status_code, 403)
