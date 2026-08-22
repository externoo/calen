from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from .utils import uuid7
# Create your models here.

class UUIDModel(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True

class Commitment(UUIDModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commitments", verbose_name=_("user"))

    date = models.DateField(_("date"), db_index=True)
    text = models.CharField(_("commitment"), max_length=200)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    

    class Meta:
        verbose_name = _("commitment")
        verbose_name_plural = _("commitments")
        ordering = ["-created_at"]
    def __str__(self):
        return f"{self.date}: {self.text}"