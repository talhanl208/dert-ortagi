from django.contrib import admin
from django.utils import timezone

from .models import Block, Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("created_at", "target_type", "reason", "reported_username", "status")
    list_filter = ("status", "reason", "target_type")
    search_fields = ("reported_username",)
    readonly_fields = (
        "reporter",
        "reported_user",
        "reported_username",
        "target_type",
        "dert",
        "message",
        "reason",
        "detail",
        "content_snapshot",
        "created_at",
        "reviewed_at",
    )
    fields = readonly_fields + ("status", "moderator_note")
    actions = ["hide_content_and_close", "suspend_reported_users", "dismiss"]

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        if "status" in form.changed_data and obj.status != Report.Status.OPEN:
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    @admin.action(description="İçeriği gizle ve şikayeti kapat")
    def hide_content_and_close(self, request, queryset):
        count = 0
        for report in queryset.select_related("dert", "message"):
            if report.dert:
                report.dert.is_hidden = True
                report.dert.hidden_reason = "Topluluk kurallarına aykırı bulundu."
                report.dert.save(update_fields=["is_hidden", "hidden_reason"])
            if report.message:
                report.message.delete()
            report.status = Report.Status.ACTION_TAKEN
            report.reviewed_at = timezone.now()
            report.save(update_fields=["status", "reviewed_at"])
            count += 1
        self.message_user(request, f"{count} şikayet için içerik kaldırıldı.")

    @admin.action(description="Şikayet edilen kullanıcıları askıya al")
    def suspend_reported_users(self, request, queryset):
        users = {r.reported_user for r in queryset if r.reported_user and not r.reported_user.is_superuser}
        for user in users:
            user.is_active = False
            user.save(update_fields=["is_active"])
        queryset.update(status=Report.Status.ACTION_TAKEN, reviewed_at=timezone.now())
        self.message_user(request, f"{len(users)} hesap askıya alındı.")

    @admin.action(description="Gerek görülmedi olarak kapat")
    def dismiss(self, request, queryset):
        n = queryset.update(status=Report.Status.DISMISSED, reviewed_at=timezone.now())
        self.message_user(request, f"{n} şikayet kapatıldı.")


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ("blocker", "blocked", "created_at")
    search_fields = ("blocker__username", "blocked__username")
    readonly_fields = ("blocker", "blocked", "created_at")

    def has_add_permission(self, request):
        return False
