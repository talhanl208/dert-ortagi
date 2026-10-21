"""
Basit, bağımlılıksız hız sınırlama.

Önbellekte sabit pencereli bir sayaç tutar. IP adresleri önbelleğe ham hâliyle
yazılmaz; SECRET_KEY ile tuzlanmış özetleri kullanılır.
"""

import hashlib
import hmac
import time
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render


def _digest(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]


def client_ip(request) -> str:
    # X-Forwarded-For istemci tarafından taklit edilebilir; bu yüzden yalnızca
    # REMOTE_ADDR kullanılır. Ters vekil sunucu arkasında çalışırken vekil
    # sunucunun REMOTE_ADDR'ı doğru ayarlaması gerekir.
    return request.META.get("REMOTE_ADDR") or "unknown"


def _identity(request, by: str) -> str:
    if by == "user" and getattr(request, "user", None) and request.user.is_authenticated:
        return f"u:{request.user.pk}"
    return f"ip:{_digest(client_ip(request))}"


def hit(scope: str, ident: str, limit: int, period: int) -> bool:
    """Sayacı artırır; limit aşılmadıysa True döner."""
    window = int(time.time() // period)
    key = f"rl:{scope}:{ident}:{window}"
    added = cache.add(key, 1, timeout=period + 5)
    if added:
        return True
    try:
        count = cache.incr(key)
    except ValueError:  # anahtar arada silindiyse
        cache.set(key, 1, timeout=period + 5)
        return True
    return count <= limit


def is_limited(scope: str, ident: str, limit: int, period: int) -> bool:
    """Sayacı artırmadan, limitin dolup dolmadığına bakar."""
    window = int(time.time() // period)
    return (cache.get(f"rl:{scope}:{ident}:{window}") or 0) >= limit


def rate_limit(scope: str, limit: int, period: int, by: str = "ip", methods=("POST",)):
    """Görünüm dekoratörü. Limit aşılırsa 429 ve dostça bir sayfa döner."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method in methods:
                ident = _identity(request, by)
                if not hit(scope, ident, limit, period):
                    return render(
                        request,
                        "core/ratelimited.html",
                        {"wait_minutes": max(1, period // 60)},
                        status=429,
                    )
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def username_key(username: str) -> str:
    return _digest((username or "").casefold())
