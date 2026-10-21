from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from dertler.models import Dert

from .quotes import quote_of_the_day, random_quote

LEGAL_PAGES = {
    "aydinlatma-metni": ("core/legal/aydinlatma.html", "KVKK Aydınlatma Metni"),
    "acik-riza-metni": ("core/legal/acik_riza.html", "Açık Rıza Metni"),
    "kullanim-kosullari": ("core/legal/kullanim_kosullari.html", "Kullanım Koşulları"),
    "topluluk-kurallari": ("core/legal/topluluk_kurallari.html", "Topluluk Kuralları"),
    "cerez-politikasi": ("core/legal/cerez_politikasi.html", "Çerez Politikası"),
}


def home(request):
    latest = Dert.objects.visible_to(request.user).select_related("author", "category").with_counts()[:6]
    today = quote_of_the_day()
    band = random_quote()
    while band["text"] == today["text"]:
        band = random_quote()
    return render(request, "core/home.html", {"latest": latest, "band_quote": band})


def support(request):
    return render(request, "core/destek.html")


def legal(request, slug):
    if slug not in LEGAL_PAGES:
        raise Http404
    template, title = LEGAL_PAGES[slug]
    return render(
        request,
        template,
        {
            "page_title": title,
            "controller": settings.DATA_CONTROLLER,
            "retention": settings.RETENTION_DAYS,
            "report_threshold": settings.AUTO_HIDE_REPORT_THRESHOLD,
            "legal_pages": LEGAL_PAGES,
            "current_slug": slug,
        },
    )


def error_404(request, exception=None):
    return render(request, "core/error.html", {"code": 404, "title": "Bu sayfayı bulamadık"}, status=404)


def error_403(request, exception=None):
    return render(request, "core/error.html", {"code": 403, "title": "Bu sayfaya erişimin yok"}, status=403)


def error_500(request):
    # İstek bağlamı olmadan çiz: hata veritabanından kaynaklanıyorsa
    # bağlam işlemcileri tekrar hata vermesin.
    return render(None, "core/error.html", {"code": 500, "title": "Bir şeyler ters gitti"}, status=500)
