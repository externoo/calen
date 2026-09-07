from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser
# Register your models here.


class CustomUserAdmin(UserAdmin):
    """Stock UserAdmin plus the one field this project adds.

    `UserAdmin.fieldsets` is an explicit list of field names, so a new model
    field is simply absent from the admin until it is named here - no error,
    no warning, just a form that silently cannot edit it. Subclassing is
    still much safer than a plain ModelAdmin, which would render `password`
    as an editable text box and save whatever was typed as the hash.
    """

    fieldsets = UserAdmin.fieldsets + (
        (_("Telegram"), {"fields": ("telegram_chat_id",)}),
    )


admin.site.register(CustomUser, CustomUserAdmin)
