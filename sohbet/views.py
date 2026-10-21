from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.decorators import special_consent_required
from core.ratelimit import rate_limit
from core.text import looks_like_crisis
from dertler.models import Dert, Reaction

from .forms import MessageForm, RequestForm
from .models import Conversation
from .services import ChatError, close_conversation, send_message, start_conversation

User = get_user_model()


def _get_conversation(request, public_id):
    """Yalnızca sohbetin taraflarının erişebildiği nesne (IDOR koruması)."""
    conv = get_object_or_404(
        Conversation.objects.select_related("initiator", "recipient", "dert", "dert__category"),
        public_id=public_id,
    )
    if not conv.is_participant(request.user):
        raise Http404
    return conv


@login_required
def inbox(request):
    user = request.user
    base = Conversation.objects.for_user(user).select_related("initiator", "recipient", "dert").with_unread(user)

    def prepare(qs):
        rows = list(qs)
        for conv in rows:
            conv.display = conv.other_display(user)
        return rows

    return render(
        request,
        "sohbet/inbox.html",
        {
            "incoming": prepare(base.filter(recipient=user, status=Conversation.Status.PENDING)),
            "outgoing": prepare(base.filter(initiator=user, status=Conversation.Status.PENDING)),
            "active": prepare(base.filter(status=Conversation.Status.ACTIVE)),
            "past": prepare(base.filter(status__in=[Conversation.Status.CLOSED, Conversation.Status.DECLINED])[:20]),
        },
    )


@special_consent_required
@rate_limit("chat-request", limit=10, period=3600, by="user")
def request_chat(request, public_id):
    """Bir derdin sahibine sohbet isteği gönder."""
    dert = get_object_or_404(Dert.objects.select_related("author", "category"), public_id=public_id, is_hidden=False)
    if dert.author_id == request.user.pk:
        return redirect(dert)
    from guvenlik.models import Block

    if Block.objects.between(request.user, dert.author).exists():
        raise Http404
    if not dert.open_to_chat:
        messages.info(request, "Bu dert şu anda sohbet isteklerine kapalı.")
        return redirect(dert)

    form = RequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            conv = start_conversation(request.user, dert.author, dert, form.cleaned_data["intro"])
        except ChatError as exc:
            messages.error(request, str(exc))
            return redirect(dert)
        messages.success(request, "İsteğin gönderildi. Kabul edilince burada sohbet edebileceksiniz.")
        return redirect(conv)
    return render(request, "sohbet/request.html", {"form": form, "dert": dert, "target": None})


@special_consent_required
@rate_limit("chat-request", limit=10, period=3600, by="user")
def match_request(request, public_id, user_id):
    """
    Dert sahibi, derdine "ben de yaşıyorum" diyen birine sohbet isteği gönderir.
    Yalnızca gerçekten tepki vermiş kişilere istek gönderilebilir.
    """
    dert = get_object_or_404(Dert, public_id=public_id, author=request.user)
    target = get_object_or_404(User, public_id=user_id, is_active=True)
    if not Reaction.objects.filter(dert=dert, user=target, kind=Reaction.Kind.METOO).exists():
        raise Http404

    form = RequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            conv = start_conversation(request.user, target, dert, form.cleaned_data["intro"])
        except ChatError as exc:
            messages.error(request, str(exc))
            return redirect(dert)
        messages.success(request, f"{target.username} kişisine istek gönderdin.")
        return redirect(conv)
    return render(request, "sohbet/request.html", {"form": form, "dert": dert, "target": target})


@login_required
def detail(request, public_id):
    conv = _get_conversation(request, public_id)
    conv.mark_read(request.user)
    msgs = list(conv.messages.select_related("sender").order_by("created_at", "pk")[:500])
    return render(
        request,
        "sohbet/detail.html",
        {
            "conv": conv,
            "who": conv.other_display(request.user),
            "chat_messages": msgs,
            "last_id": msgs[-1].pk if msgs else 0,
            "form": MessageForm(),
            "is_recipient": conv.recipient_id == request.user.pk,
        },
    )


@special_consent_required
@require_POST
@rate_limit("chat-send", limit=30, period=60, by="user")
def send(request, public_id):
    conv = _get_conversation(request, public_id)
    form = MessageForm(request.POST)
    if form.is_valid():
        try:
            send_message(conv, request.user, form.cleaned_data["body"])
        except ChatError as exc:
            messages.error(request, str(exc))
        else:
            if looks_like_crisis(form.cleaned_data["body"]):
                messages.warning(request, "crisis", extra_tags="crisis")
    else:
        messages.error(request, form.errors.get("body", ["Mesaj gönderilemedi."])[0])
    return redirect(conv.get_absolute_url() + "#yaz")


@login_required
@require_GET
def poll(request, public_id):
    """Yeni mesajları JSON olarak döner. İçerik istemcide textContent ile basılır."""
    conv = _get_conversation(request, public_id)
    try:
        after = max(0, int(request.GET.get("after", 0)))
    except ValueError:
        after = 0
    new = conv.messages.filter(pk__gt=after).order_by("created_at", "pk")[:100]
    data = [
        {
            "id": m.pk,
            "mine": m.sender_id == request.user.pk,
            "body": m.body,
            "time": timezone.localtime(m.created_at).strftime("%H:%M"),
        }
        for m in new
    ]
    if data:
        conv.mark_read(request.user)
    return JsonResponse({"status": conv.status, "messages": data})


@login_required
@require_POST
def accept(request, public_id):
    conv = _get_conversation(request, public_id)
    if conv.recipient_id != request.user.pk or conv.status != Conversation.Status.PENDING:
        raise Http404
    conv.status = Conversation.Status.ACTIVE
    conv.save(update_fields=["status", "updated_at"])
    messages.success(request, "Sohbet başladı. Nazik olmayı unutmayın. 🫖")
    return redirect(conv)


@login_required
@require_POST
def decline(request, public_id):
    conv = _get_conversation(request, public_id)
    if conv.recipient_id != request.user.pk or conv.status != Conversation.Status.PENDING:
        raise Http404
    conv.status = Conversation.Status.DECLINED
    conv.closed_at = timezone.now()
    conv.save(update_fields=["status", "closed_at", "updated_at"])
    messages.info(request, "İsteği reddettin. Karşı tarafa bir neden gösterilmez.")
    return redirect("sohbet:inbox")


@login_required
@require_POST
def close(request, public_id):
    conv = _get_conversation(request, public_id)
    if not conv.is_open:
        raise Http404
    close_conversation(conv)
    messages.info(request, "Sohbeti sonlandırdın.")
    return redirect("sohbet:inbox")
