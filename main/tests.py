import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Commitment

# Create your tests here.
class DayViewTests(TestCase):
    #the name of the test is important for setup, because it will be used to create a unique database for each test method
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester", password="pw-for-tests-only"
        )
        self.url = reverse("day", args=[2026, 1, 15])

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_logged_in_user_gets_the_day_page(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main/day.html")
        self.assertEqual(response.context["date"].isoformat(), "2026-01-15")

    def test_posting_a_commitment_saves_it_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"text": "Test Commitment"})
        #this raises DoesNotExist if there are zero rows and MultipleObjectsReturned if there's more than one
        #That only works because of test isolation: TestCase wraps each test method in a database transaction and rolls it back afterwards.
        commitment = Commitment.objects.get()
        
        self.assertEqual(commitment.text, "Test Commitment")
        self.assertEqual(commitment.user, self.user)
        self.assertEqual(commitment.date, datetime.date(2026, 1, 15))

        self.assertRedirects(response, self.url)