from django.contrib import admin

from .models import Commitment
# Register your models here.

@admin.register(Commitment)
class CommitmentAdmin(admin.ModelAdmin):
    list_display = ("date", "text", "user", "created_at")
    list_filter = ("date", "user")
    search_fields = ("text",)
    date_hierarchy = "date"
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)