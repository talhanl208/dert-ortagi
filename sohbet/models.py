import uuid

from django.conf import settings
from django.db import models
from django.db.models import BooleanField, Case, Exists, OuterRef, Q, Value, When
from django.urls import reverse
from django.utils import timezone


class ConversationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(Q(initiator=user) | Q(recipient=user))

    def open(self):
        return self.filter(status__in=[Conversation.Status.PENDING, Conversation.Status.ACTIVE])

    def with_unread(self, user):
        others = Message.objects.filter(conversation=OuterRef("pk")).exclude(sender=user)
        return self.annotate(
            unread=Case(
                When(initiator=user, then=Exists(others.filter(created_at__gt=OuterRef("initiator_last_read")))),
                When(recipient=user, then=Exists(others.filter(created_at__gt=OuterRef("recipient_last_read")))),
                default=Value(False),
                output_field=BooleanField(),
            )
        )

    def attention_count(self, user) -> int:
        """Bekleyen istekler + okunmamış mesajı olan sohbetler."""
        pending = self.filter(recipient=user, status=Conversation.Status.PENDING).count()
        unread = (
            self.for_user(user).filter(status=Conversation.Status.ACTIVE).with_unread(user).filter(unread=True).count()
        )
        return pending + unread


class Conversation(models.Model):
    """
    İki kişi arasındaki sohbet. Başlatan kişi önce kısa bir istek mesajı
    yazar; karşı taraf kabul etmeden tek bir mesaj bile gönderilemez.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "İstek bekliyor"
        ACTIVE = "active", "Devam ediyor"
        DECLINED = "declined", "Reddedildi"
        CLOSED = "closed", "Sona erdi"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    dert = models.ForeignKey(
        "dertler.Dert", on_delete=models.SET_NULL, null=True, blank=True, related_name="conversations"
    )
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="started_conversations"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_conversations"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    intro = models.TextField("istek mesajı", max_length=500, blank=True)
    # Anonim bir derdin sahibi sohbette de anonim kalır.
    initiator_anonymous = models.BooleanField(default=False)
    recipient_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    initiator_last_read = models.DateTimeField(default=timezone.now)
    recipient_last_read = models.DateTimeField(default=timezone.now)

    objects = ConversationQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "sohbet"
        verbose_name_plural = "sohbetler"
        constraints = [
            models.UniqueConstraint(
                fields=["dert", "initiator", "recipient"],
                condition=Q(status__in=["pending", "active"]),
                name="one_open_conversation_per_pair_and_dert",
            ),
            models.CheckConstraint(
                condition=~Q(initiator=models.F("recipient")),
                name="no_conversation_with_self",
            ),
        ]

    def __str__(self):
        return f"{self.initiator} ↔ {self.recipient} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("sohbet:detail", args=[self.public_id])

    def is_participant(self, user) -> bool:
        return user.pk in (self.initiator_id, self.recipient_id)

    def other(self, user):
        return self.recipient if user.pk == self.initiator_id else self.initiator

    def other_display(self, user):
        """Karşı tarafın bu kullanıcıya gösterilecek adı ve avatarı."""
        other = self.other(user)
        hidden = self.recipient_anonymous if other.pk == self.recipient_id else self.initiator_anonymous
        if hidden:
            return {"name": "Anonim dert ortağı", "avatar": "🫖", "anonymous": True}
        return {"name": other.username, "avatar": other.avatar, "anonymous": False}

    def mark_read(self, user):
        now = timezone.now()
        field = "initiator_last_read" if user.pk == self.initiator_id else "recipient_last_read"
        Conversation.objects.filter(pk=self.pk).update(**{field: now})
        setattr(self, field, now)

    @property
    def is_open(self):
        return self.status in (self.Status.PENDING, self.Status.ACTIVE)


class Message(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField("mesaj", max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at", "pk"]
        verbose_name = "mesaj"
        verbose_name_plural = "mesajlar"

    def __str__(self):
        return f"Mesaj #{self.pk}"
