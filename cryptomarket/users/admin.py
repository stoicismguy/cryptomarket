from django.contrib import admin
from .models import User


class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "role", "api_key", "is_superuser")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("name",)

admin.site.register(User, UserAdmin)
