import json

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.quotes import random_quote
from core.ratelimit import rate_limit

from .forms import (
    DeleteAccountForm,
    LoginForm,
    PasswordConfirmForm,
    RegisterForm,
    SettingsForm,
    SpecialConsentForm,
)
from .models import AVATAR_CHOICES, NICK_ADJECTIVES, suggest_nickname
from .services import (
    export_user_data,
    give_special_consent,
    record_terms_acceptance,
    withdraw_special_consent,
)


def _safe_next(request, fallback):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return nxt
    return fallback


@rate_limit("register", limit=5, period=3600)
def register(request):
    if request.user.is_authenticated:
        return redirect("dertler:list")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            record_terms_acceptance(user)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"Hoş geldin {user.username}! {user.avatar}")
            return redirect("accounts:consent")
    else:
        form = RegisterForm(initial={"username": suggest_nickname()})
    return render(
        request,
        "accounts/register.html",
        {
            "form": form,
            "nick_words": {
                "adjectives": NICK_ADJECTIVES,
                "animals": [name for _, name in AVATAR_CHOICES],
            },
        },
    )


@method_decorator(rate_limit("login", limit=20, period=600), name="dispatch")
class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


@login_required
def settings_view(request):
    if request.method == "POST":
        form = SettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Ayarların kaydedildi.")
            return redirect("accounts:settings")
    else:
        form = SettingsForm(instance=request.user)
    return render(request, "accounts/settings.html", {"form": form})


@login_required
def consent(request):
    """Özel nitelikli veriler için ayrı açık rıza adımı (isteğe bağlı)."""
    next_url = _safe_next(request, reverse_lazy("dertler:create"))
    if request.user.has_special_consent and request.method == "GET":
        return render(request, "accounts/consent_status.html", {"withdraw_form": PasswordConfirmForm(request.user)})

    if request.method == "POST":
        form = SpecialConsentForm(request.POST)
        if form.is_valid():
            give_special_consent(request.user)
            messages.success(request, "Teşekkürler. Artık derdini anlatabilir ve sohbet edebilirsin.")
            return redirect(next_url)
    else:
        form = SpecialConsentForm()
    return render(request, "accounts/consent.html", {"form": form, "next": next_url})


@login_required
@require_POST
def withdraw_consent(request):
    form = PasswordConfirmForm(request.user, request.POST)
    if form.is_valid():
        withdraw_special_consent(request.user)
        messages.info(
            request,
            "Açık rızanı geri aldın. Dertlerin, 'ben de' tepkilerin ve mesajların silindi.",
        )
        return redirect("accounts:settings")
    return render(request, "accounts/consent_status.html", {"withdraw_form": form})


@login_required
@rate_limit("export", limit=5, period=3600, by="user", methods=("GET",))
def export_data(request):
    data = export_user_data(request.user)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    stamp = timezone.now().strftime("%Y%m%d")
    response = HttpResponse(payload, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="dert-ortagi-verilerim-{stamp}.json"'
    return response


@login_required
def delete_account(request):
    if request.method == "POST":
        form = DeleteAccountForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.info(request, "Hesabın ve tüm verilerin silindi. Kendine iyi bak. 🌻")
            return redirect("core:home")
    else:
        form = DeleteAccountForm(request.user)
    return render(request, "accounts/delete.html", {"form": form, "quote": random_quote()})


# --------------------------------------------------------------------------
# Parola değiştirme / sıfırlama — tek bir sade şablon kullanılır
# --------------------------------------------------------------------------
SIMPLE = "accounts/simple_form.html"


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = SIMPLE
    success_url = reverse_lazy("accounts:password_change_done")
    extra_context = {"title": "Parolanı değiştir", "submit": "Parolayı değiştir"}


class PasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name = SIMPLE
    extra_context = {"title": "Parolan değişti", "message": "Yeni parolan kaydedildi."}


@method_decorator(rate_limit("password-reset", limit=5, period=3600), name="dispatch")
class PasswordResetView(auth_views.PasswordResetView):
    template_name = SIMPLE
    email_template_name = "accounts/email/password_reset.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    extra_context = {
        "title": "Parolanı sıfırla",
        "intro": "Hesabına e-posta eklediysen, sıfırlama bağlantısını oraya göndereceğiz.",
        "submit": "Bağlantıyı gönder",
    }


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = SIMPLE
    extra_context = {
        "title": "E-postanı kontrol et",
        "message": "Bu adrese bağlı bir hesap varsa, sıfırlama bağlantısı birkaç dakika içinde gelir.",
    }


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = SIMPLE
    success_url = reverse_lazy("accounts:password_reset_complete")
    extra_context = {"title": "Yeni parolanı belirle", "submit": "Parolayı kaydet"}


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = SIMPLE
    extra_context = {"title": "Parolan yenilendi", "message": "Artık yeni parolanla giriş yapabilirsin."}
