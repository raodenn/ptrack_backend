from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()

class AccountsAuthTests(APITestCase):

    def setUp(self):
        self.user_password = 'testpassword'
        self.user = User.objects.create_user(
            email='test@example.com',
            password=self.user_password,
            username='testuser'
        )

        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.refresh_url = reverse('accounts:token_refresh')

    def test_registration_success(self):
        data = {
            'email': 'newuser@example.com',
            'password': 'newpassword123!',
            'password2': 'newpassword123!',  
            'username': 'newuser'
        }

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])

        new_user = User.objects.get(email='newuser@example.com')
        self.assertIsNotNone(new_user)
        self.assertTrue(new_user.check_password('newpassword123!'))

    def test_registration_mismatched_passwords(self):
        data = {
            'email': 'newuser@example.com',
            'password': 'newpassword123!',
            'password2': 'differentpassword123!'
        }

        response = self.client.post(self.register_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_login_success(self):
        data = {
            'email': self.user.email,
            'password': self.user_password
        }

        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_logout_and_blacklist(self):
        data = {
            'email': self.user.email,
            'password': self.user_password
        }
        login_response = self.client.post(self.login_url, data)

        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        logout_response = self.client.post(self.logout_url, {'refresh': refresh_token})

        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_attempt = self.client.post(self.refresh_url, {'refresh': refresh_token})

        self.assertEqual(refresh_attempt.status_code, status.HTTP_401_UNAUTHORIZED)