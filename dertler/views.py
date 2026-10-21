import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import special_consent_required
from core.quotes import random_quote
from core.ratelimit import rate_limit
from core.text import looks_like_crisis
from sohbet.models import Conversation

from .forms import DertForm, FilterForm
from .matching import similar_dertler
from .models import Category, Dert, Reaction

PAGE_SIZE = 12


def _get_visible_dert(request, public_id):
    dert = get_object_or_404(Dert.objects.select_related("author", "category"), public_id=public_id)
    is_owner = request.user.is_authenticated and dert.author_id == request.user.pk
    if is_owner:
        return dert, True
    if dert.is_hidden:
        raise Http404
    if request.user.is_authenticated:
        from guvenlik.models import Block

        if Block.objects.between(request.user, dert.author).exists():
            raise Http404
    return dert, False


def _get_own_dert(request, public_id):
    return get_object_or_404(Dert, public_id=public_id, author=request.user)


def dert_list(request):
    form = FilterForm(request.GET or None)
    qs = Dert.objects.visible_to(request.user).select_related("author", "category").with_counts()
    active_category = None
    query = ""
    if form.is_valid():
        query = form.cleaned_data.get("q", "").strip()
        slug = form.cleaned_data.get("kategori")
        if slug:
            active_category = Category.objects.filter(slug=slug).first()
            if active_category:
                qs = qs.filter(category=active_category)
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(summary__icontains=query))
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("sayfa"))
    return render(
        request,
        "dertler/list.html",
        {
            "page": page,
            "categories": Category.objects.all(),
            "active_category": active_category,
            "query": query,
        },
    )


def dert_detail(request, public_id):
    dert, is_owner = _get_visible_dert(request, public_id)
    counts = dert.reactions.values("kind").annotate(n=Count("id"))
    count_map = {row["kind"]: row["n"] for row in counts}
    my_reactions = set()
    conversation = None
    metoo_users = []
    pending_requests = 0
    if request.user.is_authenticated:
        my_reactions = set(dert.reactions.filter(user=request.user).values_list("kind", flat=True))
        if is_owner:
            from guvenlik.models import Block

            blocked = Block.objects.related_user_ids(request.user)
            metoo_users = [
                r.user
                for r in dert.reactions.filter(kind=Reaction.Kind.METOO)
                .exclude(user_id__in=blocked)
                .select_related("user")
                .order_by("-created_at")[:20]
            ]
            pending_requests = dert.conversations.filter(
                recipient=request.user, status=Conversation.Status.PENDING
            ).count()
        else:
            conversation = (
                Conversation.objects.for_user(request.user)
                .filter(dert=dert)
                .exclude(status=Conversation.Status.DECLINED)
                .order_by("-created_at")
                .first()
            )
    reactions = [
        {"kind": kind, "label": label, "emoji": emoji, "count": count_map.get(kind, 0), "mine": kind in my_reactions}
        for kind, label, emoji in (
            (Reaction.Kind.HUG, "Sarıl", "🤗"),
            (Reaction.Kind.STRENGTH, "Güç gönder", "💪"),
            (Reaction.Kind.METOO, "Ben de yaşıyorum", "🙋"),
        )
    ]
    return render(
        request,
        "dertler/detail.html",
        {
            "dert": dert,
            "is_owner": is_owner,
            "reactions": reactions,
            "similar": similar_dertler(dert, request.user, limit=4, only_open=is_owner),
            "conversation": conversation,
            "metoo_users": metoo_users,
            "pending_requests": pending_requests,
            "quote": random_quote(),
        },
    )


@special_consent_required
@rate_limit("dert-create", limit=6, period=3600, by="user")
def dert_create(request):
    if request.method == "POST":
        form = DertForm(request.POST)
        if form.is_valid():
            dert = form.save(commit=False)
            dert.author = request.user
            dert.save()
            if looks_like_crisis(dert.title, dert.summary):
                messages.warning(request, "crisis", extra_tags="crisis")
            messages.success(request, "Derdini paylaştın. Bunu yapmak cesaret ister. 💛")
            return redirect(dert)
    else:
        initial = {}
        slug = request.GET.get("kategori")
        if slug:
            cat = Category.objects.filter(slug=slug).first()
            if cat:
                initial["category"] = cat.pk
        form = DertForm(initial=initial)
    return render(request, "dertler/form.html", {"form": form, "quote": random_quote(), "editing": False})


@special_consent_required
def dert_edit(request, public_id):
    dert = _get_own_dert(request, public_id)
    if request.method == "POST":
        form = DertForm(request.POST, instance=dert)
        if form.is_valid():
            form.save()
            messages.success(request, "Derdin güncellendi.")
            return redirect(dert)
    else:
        form = DertForm(instance=dert)
    return render(request, "dertler/form.html", {"form": form, "dert": dert, "editing": True})


@login_required
@require_POST
def dert_delete(request, public_id):
    dert = _get_own_dert(request, public_id)
    dert.delete()
    messages.info(request, "Derdin silindi.")
    return redirect("dertler:mine")


@login_required
@require_POST
def dert_status(request, public_id):
    dert = _get_own_dert(request, public_id)
    dert.status = Dert.Status.ACTIVE if dert.status == Dert.Status.LIGHTER else Dert.Status.LIGHTER
    dert.save(update_fields=["status", "updated_at"])
    if dert.status == Dert.Status.LIGHTER:
        messages.success(request, "Derdinin hafiflediğine çok sevindik! 🌤️")
    return redirect(dert)


@login_required
@require_POST
@rate_limit("react", limit=60, period=600, by="user")
def react(request, public_id):
    dert, is_owner = _get_visible_dert(request, public_id)
    kind = request.POST.get("kind")
    if kind not in Reaction.Kind.values:
        raise Http404
    if is_owner:
        messages.info(request, "Kendi derdine tepki veremezsin ama kendine sarılabilirsin. 🤗")
        return redirect(dert)
    if kind == Reaction.Kind.METOO and not request.user.has_special_consent:
        # "Ben de yaşıyorum" demek özel nitelikli veri açığa çıkarabilir.
        return redirect(reverse("accounts:consent") + "?" + urlencode({"next": dert.get_absolute_url()}))
    reaction, created = Reaction.objects.get_or_create(dert=dert, user=request.user, kind=kind)
    if not created:
        reaction.delete()
    elif kind == Reaction.Kind.METOO:
        messages.info(
            request,
            "Yalnız değilsin. Dert sahibi seni görebilir ve sana sohbet isteği gönderebilir.",
        )
    return redirect(dert)


@login_required
def my_dertler(request):
    dertler = (
        Dert.objects.filter(author=request.user)
        .select_related("category")
        .with_counts()
        .annotate(
            pending=Count(
                "conversations",
                filter=Q(conversations__status=Conversation.Status.PENDING, conversations__recipient=request.user),
                distinct=True,
            )
        )
    )
    return render(request, "dertler/mine.html", {"dertler": dertler})


@login_required
def listen(request):
    """Dinleyici gönüllüleri için: henüz kimseyle konuşamamış dertler."""
    user = request.user
    dertler = Dert.objects.none()
    if user.is_listener:
        since = timezone.now() - datetime.timedelta(days=30)
        dertler = (
            Dert.objects.visible_to(user)
            .filter(
                show_to_listeners=True,
                open_to_chat=True,
                status=Dert.Status.ACTIVE,
                created_at__gte=since,
            )
            .exclude(author=user)
            .exclude(conversations__initiator=user)
            .annotate(
                talks=Count(
                    "conversations",
                    filter=Q(conversations__status=Conversation.Status.ACTIVE),
                    distinct=True,
                )
            )
            .select_related("author", "category")
            .with_counts()
            .order_by("talks", "created_at")
        )
        cats = list(user.listener_categories.all())
        if cats:
            dertler = dertler.filter(category__in=cats)
        dertler = dertler[:24]
    return render(request, "dertler/listen.html", {"dertler": dertler})
