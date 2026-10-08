from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.finance.models import Invoice, Payment
from apps.rental.models import Rental

User = get_user_model()


class InvoiceModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='customer', password='pass')
        self.now = timezone.now()
        self.rental = Rental.objects.create(
            customer=self.user,
            start_at=self.now,
            end_at=self.now + timedelta(hours=2),
        )

    def test_create_invoice(self):
        invoice = Invoice.objects.create(
            rental=self.rental,
            customer=self.user,
            total_amount=Decimal('50.00'),
        )
        self.assertEqual(invoice.status, Invoice.Status.DRAFT)
        self.assertEqual(invoice.total_amount, Decimal('50.00'))

    def test_invoice_str(self):
        invoice = Invoice.objects.create(
            rental=self.rental,
            customer=self.user,
            total_amount=Decimal('50.00'),
        )
        self.assertIn(str(invoice.pk), str(invoice))
        self.assertIn('Draft', str(invoice))


class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='payer', password='pass')
        self.now = timezone.now()
        self.rental = Rental.objects.create(
            customer=self.user,
            start_at=self.now,
            end_at=self.now + timedelta(hours=2),
        )
        self.invoice = Invoice.objects.create(
            rental=self.rental,
            customer=self.user,
            total_amount=Decimal('50.00'),
        )

    def test_create_payment(self):
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('50.00'),
            method=Payment.Method.CASH,
        )
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_payment_str(self):
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('25.00'),
            method=Payment.Method.CARD,
        )
        self.assertIn('25.00', str(payment))
        self.assertIn('Pending', str(payment))


class FinanceAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='admin123',
        )
        self.client.force_login(self.superuser)

    def test_invoice_changelist(self):
        response = self.client.get('/admin/finance/invoice/')
        self.assertEqual(response.status_code, 200)

    def test_payment_changelist(self):
        response = self.client.get('/admin/finance/payment/')
        self.assertEqual(response.status_code, 200)


class FinanceAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='apiuser', password='pass')
        self.client.force_login(self.user)

    def test_list_invoices(self):
        response = self.client.get('/api/v1/finance/invoices/')
        self.assertEqual(response.status_code, 200)

    def test_list_payments(self):
        response = self.client.get('/api/v1/finance/payments/')
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_access_denied(self):
        self.client.logout()
        response = self.client.get('/api/v1/finance/invoices/')
        self.assertEqual(response.status_code, 403)
