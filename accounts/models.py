from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from main.utils import uuid7
# Create your models here.

class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")