from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Conversation, Message

MAX_PENDING_REQUESTS = 10


class ChatError(Exception):
    """Kullanıcıya gösterilebilecek, açıklayıcı hata."""


def check_can_request(initiator, recipient, dert):
    from guvenlik.models import Block

    if initiator.pk == recipient.pk:
        raise ChatError("Kendinle sohbet başlatamazsın.")
    if not recipient.is_active:
        raise ChatError("Bu kişiye şu anda ulaşılamıyor.")
    if Block.objects.between(initiator, recipient).exists():
        raise ChatError("Bu kişiye ulaşılamıyor.")
    if Conversation.objects.filter(dert=dert, initiator=initiator, recipient=recipient).open().exists():
        raise ChatError("Bu dert için zaten açık bir sohbetin var.")
    pending = Conversation.objects.filter(initiator=initiator, status=Conversation.Status.PENDING).count()
    if pending >= MAX_PENDING_REQUESTS:
        raise ChatError("Yanıt bekleyen çok fazla isteğin var. Biraz bekle ya da eski isteklerini geri çek.")


def start_conversation(initiator, recipient, dert, intro) -> Conversation:
    check_can_request(initiator, recipient, dert)
    try:
        with transaction.atomic():
            return Conversation.objects.create(
                initiator=initiator,
                recipient=recipient,
                dert=dert,
                intro=intro,
                initiator_anonymous=bool(dert and dert.is_anonymous and dert.author_id == initiator.pk),
                recipient_anonymous=bool(dert and dert.is_anonymous and dert.author_id == recipient.pk),
            )
    except IntegrityError as exc:
        raise ChatError("Bu dert için zaten açık bir sohbetin var.") from exc


def send_message(conversation, sender, body) -> Message:
    from guvenlik.models import Block

    if conversation.status != Conversation.Status.ACTIVE:
        raise ChatError("Bu sohbet artık açık değil.")
    other = conversation.other(sender)
    if Block.objects.between(sender, other).exists():
        raise ChatError("Bu kişiye mesaj gönderilemiyor.")
    message = Message.objects.create(conversation=conversation, sender=sender, body=body)
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    conversation.mark_read(sender)
    return message


def close_conversation(conversation):
    conversation.status = Conversation.Status.CLOSED
    conversation.closed_at = timezone.now()
    conversation.save(update_fields=["status", "closed_at", "updated_at"])
