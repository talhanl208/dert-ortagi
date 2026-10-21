from django.utils.cache import add_never_cache_headers


class PrivacyHeadersMiddleware:
    """
    - Tarayıcı özelliklerini (kamera, mikrofon, konum…) kapatır.
    - Oturum açmış kullanıcıların sayfalarının tarayıcı/ara bellekte
      saklanmasını engeller; ortak bilgisayarda "geri" tuşuyla başkasının
      mesajları görünmesin.
    """

    PERMISSIONS_POLICY = (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=(), browsing-topics=()"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Permissions-Policy", self.PERMISSIONS_POLICY)
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not request.path.startswith("/static/"):
            add_never_cache_headers(response)
        return response
