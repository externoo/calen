from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterViewTests(TestCase):
    def test_anonymous_user_can_reach_the_register_page(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_valid_post_creates_a_user_and_redirects_to_login(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password1': 'testpassword123',
            'password2': 'testpassword123',
        }, )

        user = User.objects.get()
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertTrue(user.check_password('testpassword123'))

        self.assertRedirects(response, reverse('accounts:login'))

    def test_mismatched_passwords_create_no_user(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password1': 'testpassword123',
            'password2': 'differentpassword123',
        }, )
        
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)