from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from main.utils import uuid7
# Create your models here.

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    # Telegram will not reveal a chat id on request - the user has to message
    # the bot first, and `manage.py telegram_whoami` reads it back out of
    # getUpdates. Blank (not null) is the Django convention for optional text.
    telegram_chat_id = models.CharField(
        _("Telegram chat ID"),
        max_length=32,
        blank=True,
        default="",
        help_text=_("Leave blank to receive no Telegram reminders."),
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")