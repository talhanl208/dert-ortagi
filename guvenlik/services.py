from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Block, Report


@transaction.atomic
def create_report(*, reporter, target_type, reason, detail="", dert=None, message=None, reported_user=None):
    snapshot = ""
    if dert is not None:
        reported_user = dert.author
        snapshot = f"{dert.title}\n\n{dert.summary}"
    elif message is not None:
        reported_user = message.sender
        snapshot = message.body

    report = Report.objects.create(
        reporter=reporter,
        reported_user=reported_user,
        reported_username=reported_user.username if reported_user else "",
        target_type=target_type,
        dert=dert,
        message=message,
        reason=reason,
        detail=detail,
        content_snapshot=snapshot,
    )

    # Yeterince farklı kişi şikayet ettiyse dert moderatör bakana kadar gizlenir.
    if dert is not None and not dert.is_hidden:
        reporters = Report.objects.filter(dert=dert, status=Report.Status.OPEN).values("reporter").distinct().count()
        if reporters >= settings.AUTO_HIDE_REPORT_THRESHOLD:
            dert.is_hidden = True
            dert.hidden_reason = "Birden fazla şikayet aldı, moderatör incelemesi bekleniyor."
            dert.save(update_fields=["is_hidden", "hidden_reason", "updated_at"])
    return report


def already_reported(reporter, *, dert=None, message=None, reported_user=None) -> bool:
    qs = Report.objects.filter(reporter=reporter, status=Report.Status.OPEN)
    if dert is not None:
        return qs.filter(dert=dert).exists()
    if message is not None:
        return qs.filter(message=message).exists()
    return qs.filter(target_type=Report.Target.USER, reported_user=reported_user).exists()


@transaction.atomic
def block_user(blocker, blocked, label=""):
    """Engeller ve iki kişi arasındaki açık sohbetleri kapatır."""
    from sohbet.models import Conversation

    if blocker.pk == blocked.pk:
        return None
    try:
        with transaction.atomic():
            block, _ = Block.objects.get_or_create(
                blocker=blocker, blocked=blocked, defaults={"label": label or blocked.username}
            )
    except IntegrityError:
        block = Block.objects.get(blocker=blocker, blocked=blocked)
    (
        Conversation.objects.for_user(blocker)
        .filter(initiator__in=[blocker, blocked], recipient__in=[blocker, blocked])
        .open()
        .update(status=Conversation.Status.CLOSED, closed_at=timezone.now())
    )
    return block


def unblock(blocker, block_id):
    Block.objects.filter(blocker=blocker, pk=block_id).delete()
