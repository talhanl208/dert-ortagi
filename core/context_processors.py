from django.conf import settings

from .quotes import quote_of_the_day

EMERGENCY_LINES = [
    {"number": "112", "name": "Acil Çağrı", "desc": "Hayati tehlike varsa hemen ara. Ücretsiz, 7/24."},
    {"number": "183", "name": "ALO 183 Sosyal Destek Hattı", "desc": "Şiddet, istismar ve sosyal destek için. 7/24."},
]


def site(request):
    ctx = {
        "gunun_sozu": quote_of_the_day(),
        "legal_versions": settings.LEGAL_VERSIONS,
        "emergency_lines": EMERGENCY_LINES,
        "inbox_badge": 0,
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from sohbet.models import Conversation

        ctx["inbox_badge"] = Conversation.objects.attention_count(user)
    return ctx
