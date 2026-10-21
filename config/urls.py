from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core.ratelimit import rate_limit

admin.site.site_header = "Dert Ortağı · Moderasyon"
admin.site.site_title = "Dert Ortağı Moderasyon"
admin.site.index_title = "Şikayetler ve içerik yönetimi"

# Yönetim girişine de kaba kuvvet koruması uygula.
admin.site.login = rate_limit("admin-login", limit=5, period=600)(admin.site.login)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("core.urls")),
    path("hesap/", include("accounts.urls")),
    path("dertler/", include("dertler.urls")),
    path("sohbet/", include("sohbet.urls")),
    path("guvenlik/", include("guvenlik.urls")),
]

handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
handler403 = "core.views.error_403"
