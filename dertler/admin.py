from django.contrib import admin

from .models import Category, Dert


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("emoji", "name", "slug", "color", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Dert)
class DertAdmin(admin.ModelAdmin):
    """
    Moderatörler dertleri görebilir (zaten herkese açık içerik).
    Özel mesajlar ise yönetim panelinde listelenmez; yalnızca şikayet edilen
    mesajın kopyası şikayet kaydında görünür.
    """

    list_display = ("title", "category", "author", "status", "is_hidden", "created_at")
    list_filter = ("is_hidden", "status", "category")
    search_fields = ("title", "author__username")
    readonly_fields = ("public_id", "author", "created_at", "updated_at")
    actions = ["hide", "unhide"]

    @admin.action(description="Seçili dertleri gizle")
    def hide(self, request, queryset):
        n = queryset.update(is_hidden=True, hidden_reason="Moderatör tarafından gizlendi")
        self.message_user(request, f"{n} dert gizlendi.")

    @admin.action(description="Seçili dertleri yeniden yayınla")
    def unhide(self, request, queryset):
        n = queryset.update(is_hidden=False, hidden_reason="")
        self.message_user(request, f"{n} dert yeniden yayında.")
