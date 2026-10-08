from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username='testuser', password='testpass123',
            first_name='Test', last_name='User',
            phone_number='1234567890', address='123 Test St',
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.phone_number, '1234567890')
        self.assertEqual(user.address, '123 Test St')
        self.assertTrue(user.check_password('testpass123'))

    def test_user_str_with_full_name(self):
        user = User.objects.create_user(
            username='jdoe', password='pass',
            first_name='John', last_name='Doe',
        )
        self.assertEqual(str(user), 'John Doe')

    def test_user_str_falls_back_to_username(self):
        user = User.objects.create_user(username='jdoe', password='pass')
        self.assertEqual(str(user), 'jdoe')

    def test_soft_delete(self):
        user = User.objects.create_user(username='delme', password='pass')
        self.assertIsNone(user.deleted_at)
        user.delete()
        user.refresh_from_db()
        self.assertIsNotNone(user.deleted_at)

    def test_auth_user_model_is_custom(self):
        from django.conf import settings
        self.assertEqual(settings.AUTH_USER_MODEL, 'auths.User')


class UserAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin', password='admin123',
        )
        self.client.force_login(self.superuser)

    def test_user_changelist_loads(self):
        response = self.client.get('/admin/auths/user/')
        self.assertEqual(response.status_code, 200)

    def test_user_add_page_loads(self):
        response = self.client.get('/admin/auths/user/add/')
        self.assertEqual(response.status_code, 200)


class UserAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser', password='apipass123',
        )
        self.client.force_login(self.user)

    def test_list_users(self):
        response = self.client.get('/api/v1/auth/users/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    def test_retrieve_user(self):
        response = self.client.get(f'/api/v1/auth/users/{self.user.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['username'], 'apiuser')

    def test_unauthenticated_access_denied(self):
        self.client.logout()
        response = self.client.get('/api/v1/auth/users/')
        self.assertEqual(response.status_code, 403)
