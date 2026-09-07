from django.core.management.base import BaseCommand

from main import telegram


class Command(BaseCommand):
    help = (
        "Print the chat id of everyone who has messaged the bot recently, so it "
        "can be pasted into a user's Telegram chat ID field in the admin."
    )

    def handle(self, *args, **options):
        updates = telegram.get_updates()

        seen = {}
        for update in updates:
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue
            chat = message["chat"]
            seen[chat["id"]] = chat.get("username") or chat.get("first_name") or ""

        if not seen:
            self.stdout.write(
                "No messages found.\n"
                "Open Telegram, send your bot any message, then run this again.\n"
                "(getUpdates only returns the last ~24 hours.)"
            )
            return

        self.stdout.write("chat id          from")
        for chat_id, who in seen.items():
            self.stdout.write(self.style.SUCCESS(f"{chat_id:<16} {who}"))
