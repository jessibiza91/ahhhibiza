from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "description", "timestamp")
    list_filter = ("timestamp",)
    search_fields = ("user__username", "user__email", "description")
    readonly_fields = ("timestamp",)
