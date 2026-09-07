import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from main import telegram
from main.models import Commitment


class Command(BaseCommand):
    help = (
        "Send each user a Telegram reminder listing their commitments for an "
        "upcoming day. Intended to be run once a day by a scheduler."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="How many days ahead to remind about (default: 1, i.e. tomorrow).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be sent without calling Telegram.",
        )

    def handle(self, *args, **options):
        target = timezone.localdate() + datetime.timedelta(days=options["days"])

        # One query. select_related pulls each user in the same round trip;
        # without it this is a query per commitment to read the chat id.
        commitments = (
            Commitment.objects.filter(date=target)
            .exclude(user__telegram_chat_id="")
            .select_related("user")
            .order_by("user_id", "created_at")
        )

        by_user = {}
        for commitment in commitments:
            by_user.setdefault(commitment.user, []).append(commitment)

        if not by_user:
            self.stdout.write(f"Nothing to send for {target.isoformat()}.")
            return

        for user, items in by_user.items():
            lines = [f"Reminder for {target.strftime('%A, %d %B %Y')}:"]
            lines += [f"- {commitment.text}" for commitment in items]
            text = "\n".join(lines)

            if options["dry_run"]:
                self.stdout.write(
                    f"[dry-run] -> {user.username} (chat {user.telegram_chat_id})"
                )
                self.stdout.write(text)
                continue

            telegram.send_message(user.telegram_chat_id, text)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sent {len(items)} commitment(s) to {user.username}."
                )
            )
