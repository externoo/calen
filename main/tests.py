import datetime
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
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


class CommitmentEditDeleteTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(
            username="owner", password="pw-for-tests-only"
        )
        self.other = User.objects.create_user(
            username="other", password="pw-for-tests-only"
        )
        self.commitment = Commitment.objects.create(
            user=self.owner,
            date=datetime.date(2026, 1, 15),
            text="Original text",
        )
        self.day_url = reverse("day", args=[2026, 1, 15])
        self.edit_url = reverse("commitment_edit", args=[self.commitment.pk])
        self.delete_url = reverse("commitment_delete", args=[self.commitment.pk])

    # --- edit -------------------------------------------------------------

    def test_owner_can_edit_and_no_second_row_is_created(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.edit_url, {"text": "Edited text"})

        self.commitment.refresh_from_db()
        self.assertEqual(self.commitment.text, "Edited text")
        self.assertEqual(Commitment.objects.count(), 1)
        self.assertRedirects(response, self.day_url)

    def test_other_user_cannot_edit(self):
        self.client.force_login(self.other)
        response = self.client.post(self.edit_url, {"text": "Hacked"})

        self.assertEqual(response.status_code, 404)
        self.commitment.refresh_from_db()
        self.assertEqual(self.commitment.text, "Original text")

    # --- delete -----------------------------------------------------------

    def test_owner_can_delete(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.delete_url)

        self.assertEqual(Commitment.objects.count(), 0)
        self.assertRedirects(response, self.day_url)

    def test_other_user_cannot_delete(self):
        self.client.force_login(self.other)
        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Commitment.objects.count(), 1)

    def test_get_on_delete_only_confirms_and_does_not_delete(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main/commitment_confirm_delete.html")
        self.assertEqual(Commitment.objects.count(), 1)


class SendRemindersTests(TestCase):
    """The scheduled job. Telegram itself is mocked - these test our logic,
    not the Bot API, and must never make a network call."""

    def setUp(self):
        User = get_user_model()
        self.linked = User.objects.create_user(
            username="linked", password="pw-for-tests-only", telegram_chat_id="111"
        )
        self.unlinked = User.objects.create_user(
            username="unlinked", password="pw-for-tests-only"
        )
        self.tomorrow = timezone.localdate() + datetime.timedelta(days=1)

    def test_sends_one_message_per_user_listing_all_their_commitments(self):
        Commitment.objects.create(user=self.linked, date=self.tomorrow, text="First")
        Commitment.objects.create(user=self.linked, date=self.tomorrow, text="Second")

        with patch("main.telegram.send_message") as send:
            call_command("send_reminders", stdout=StringIO())

        send.assert_called_once()
        chat_id, text = send.call_args.args
        self.assertEqual(chat_id, "111")
        self.assertIn("First", text)
        self.assertIn("Second", text)

    def test_users_without_a_chat_id_are_skipped(self):
        Commitment.objects.create(user=self.unlinked, date=self.tomorrow, text="Nope")

        with patch("main.telegram.send_message") as send:
            call_command("send_reminders", stdout=StringIO())

        send.assert_not_called()

    def test_only_the_target_day_is_included(self):
        Commitment.objects.create(user=self.linked, date=self.tomorrow, text="Soon")
        Commitment.objects.create(
            user=self.linked,
            date=self.tomorrow + datetime.timedelta(days=3),
            text="Later",
        )

        with patch("main.telegram.send_message") as send:
            call_command("send_reminders", stdout=StringIO())

        text = send.call_args.args[1]
        self.assertIn("Soon", text)
        self.assertNotIn("Later", text)

    def test_dry_run_sends_nothing(self):
        Commitment.objects.create(user=self.linked, date=self.tomorrow, text="First")

        with patch("main.telegram.send_message") as send:
            call_command("send_reminders", "--dry-run", stdout=StringIO())

        send.assert_not_called()
