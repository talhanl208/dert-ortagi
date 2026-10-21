"""
Şikayet ve engelleme.

Kullanıcı kimlikleri hiçbir herkese açık sayfada adres olarak geçmez:
engelleme ve şikayet her zaman bir dert, mesaj veya sohbet üzerinden yapılır.
Böylece anonim bir derdin sahibi, diğer dertleriyle ilişkilendirilemez.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.ratelimit import rate_limit
from dertler.models import Dert
from sohbet.models import Conversation, Message

from .forms import ReportForm
from .models import Block, Report
from .services import already_reported, block_user, create_report, unblock

TARGETS = {"dert": Report.Target.DERT, "mesaj": Report.Target.MESSAGE, "sohbet": Report.Target.USER}


def _resolve(request, target, public_id):
    """
    (rapor alanları, karşı kullanıcı, görünen ad, geri dönülecek adres) döner.
    Kullanıcının göremediği içerik şikayet edilemez/engellenemez.
    """
    user = request.user
    if target == "dert":
        dert = get_object_or_404(Dert.objects.select_related("author"), public_id=public_id, is_hidden=False)
        if dert.author_id == user.pk:
            raise Http404
        return {"dert": dert}, dert.author, dert.display_name, dert.get_absolute_url()
    if target == "mesaj":
        msg = get_object_or_404(Message.objects.select_related("conversation", "sender"), public_id=public_id)
        conv = msg.conversation
        if not conv.is_participant(user) or msg.sender_id == user.pk:
            raise Http404
        return {"message": msg}, msg.sender, conv.other_display(user)["name"], conv.get_absolute_url()
    if target == "sohbet":
        conv = get_object_or_404(Conversation.objects.select_related("initiator", "recipient"), public_id=public_id)
        if not conv.is_participant(user):
            raise Http404
        other = conv.other(user)
        return {"reported_user": other}, other, conv.other_display(user)["name"], conv.get_absolute_url()
    raise Http404


@login_required
@rate_limit("report", limit=10, period=3600, by="user")
def report(request, target, public_id):
    if target not in TARGETS:
        raise Http404
    lookup, other, label, back_url = _resolve(request, target, public_id)

    if already_reported(request.user, **lookup):
        messages.info(request, "Bunu zaten şikayet ettin. Moderatörler inceliyor.")
        return redirect(back_url)

    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        create_report(
            reporter=request.user,
            target_type=TARGETS[target],
            reason=form.cleaned_data["reason"],
            detail=form.cleaned_data["detail"],
            **lookup,
        )
        if form.cleaned_data["reason"] == Report.Reason.SELF_HARM:
            messages.warning(request, "crisis-other", extra_tags="crisis-other")
        if form.cleaned_data["also_block"]:
            block_user(request.user, other, label=label)
            messages.success(request, f"Şikayetin alındı ve {label} engellendi. Kendine iyi bak.")
            return redirect("dertler:list")
        messages.success(request, "Şikayetin alındı. Moderatörler en kısa sürede inceleyecek.")
        return redirect(back_url)

    return render(request, "guvenlik/report.html", {"form": form, "target": target, "label": label})


@login_required
@require_POST
def block(request, target, public_id):
    if target not in ("dert", "sohbet"):
        raise Http404
    _, other, label, _ = _resolve(request, target, public_id)
    block_user(request.user, other, label=label)
    messages.success(request, f"{label} engellendi. Artık birbirinizin dertlerini göremez, mesajlaşamazsınız.")
    return redirect("dertler:list")


@login_required
@require_POST
def unblock_view(request, block_id):
    unblock(request.user, block_id)
    messages.info(request, "Engeli kaldırdın.")
    return redirect("guvenlik:blocked")


@login_required
def blocked_list(request):
    blocks = Block.objects.filter(blocker=request.user).order_by("-created_at")
    return render(request, "guvenlik/blocked.html", {"blocks": blocks})
