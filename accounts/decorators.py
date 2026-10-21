from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse


def special_consent_required(view_func):
    """
    Dert yazmak, mesaj göndermek veya "ben de yaşıyorum" demek özel nitelikli
    veri (ör. sağlık) içerebilir. Bu işlemlerden önce ayrı bir açık rıza alınır.
    """

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.has_special_consent:
            url = reverse("accounts:consent") + "?" + urlencode({"next": request.get_full_path()})
            return redirect(url)
        return view_func(request, *args, **kwargs)

    return wrapper
