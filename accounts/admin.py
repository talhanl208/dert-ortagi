from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ConsentRecord, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "avatar", "is_active", "is_listener", "date_joined", "last_login", "is_staff")
    list_filter = ("is_active", "is_listener", "is_staff")
    search_fields = ("username",)
    ordering = ("-date_joined",)
    readonly_fields = (
        "public_id",
        "date_joined",
        "last_login",
        "terms_version",
        "terms_accepted_at",
        "special_consent_version",
        "special_consent_at",
    )
    fieldsets = (
        (None, {"fields": ("username", "password", "public_id")}),
        ("Profil", {"fields": ("avatar", "email", "is_listener", "listener_categories")}),
        (
            "Rızalar",
            {"fields": ("terms_version", "terms_accepted_at", "special_consent_version", "special_consent_at")},
        ),
        ("Yetkiler", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Tarihler", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("username", "password1", "password2")}),)
    actions = ["suspend_users", "reactivate_users"]

    @admin.action(description="Seçili hesapları askıya al (giriş yapamazlar)")
    def suspend_users(self, request, queryset):
        updated = queryset.exclude(is_superuser=True).update(is_active=False)
        self.message_user(request, f"{updated} hesap askıya alındı.")

    @admin.action(description="Seçili hesapları yeniden etkinleştir")
    def reactivate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} hesap etkinleştirildi.")


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "action", "version", "created_at")
    list_filter = ("kind", "action", "version")
    search_fields = ("user__username",)
    readonly_fields = ("user", "kind", "action", "version", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
