from django.conf import settings
from django.db import models
from django.db.models import Q


class BlockQuerySet(models.QuerySet):
    def between(self, a, b):
        """İki kişi arasında (her iki yönde) engelleme var mı?"""
        return self.filter(Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a))

    def related_user_ids(self, user) -> set[int]:
        """Kullanıcının engellediği ve onu engelleyen herkes."""
        rows = self.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id")
        ids = {uid for pair in rows for uid in pair}
        ids.discard(user.pk)
        return ids


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received")
    # Engelleyen kişinin gördüğü ad. Anonim bir derdin sahibi engellendiyse
    # gerçek rumuzu engelleme listesinde de gizli kalır.
    label = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = BlockQuerySet.as_manager()

    class Meta:
        verbose_name = "engelleme"
        verbose_name_plural = "engellemeler"
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block"),
            models.CheckConstraint(condition=~Q(blocker=models.F("blocked")), name="no_self_block"),
        ]

    def __str__(self):
        return f"{self.blocker} ⛔ {self.blocked}"


class Report(models.Model):
    class Target(models.TextChoices):
        DERT = "dert", "Dert"
        MESSAGE = "message", "Mesaj"
        USER = "user", "Kullanıcı (sohbetten)"

    class Reason(models.TextChoices):
        HARASSMENT = "harassment", "Taciz, zorbalık veya hakaret"
        THREAT = "threat", "Tehdit veya şiddet"
        SEXUAL = "sexual", "Cinsel içerik veya uygunsuz teklif"
        HATE = "hate", "Nefret söylemi veya ayrımcılık"
        SCAM = "scam", "Dolandırıcılık, para veya kişisel bilgi isteme"
        SPAM = "spam", "Spam veya reklam"
        MINOR = "minor", "18 yaşından küçük olduğunu düşünüyorum"
        SELF_HARM = "self_harm", "Kendine zarar verme riski — endişeliyim"
        OTHER = "other", "Başka bir şey"

    class Status(models.TextChoices):
        OPEN = "open", "Açık"
        ACTION_TAKEN = "action", "İşlem yapıldı"
        DISMISSED = "dismissed", "Gerek görülmedi"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reports_made"
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reports_received"
    )
    reported_username = models.CharField(max_length=24, blank=True)
    target_type = models.CharField(max_length=10, choices=Target.choices)
    dert = models.ForeignKey("dertler.Dert", on_delete=models.SET_NULL, null=True, blank=True)
    message = models.ForeignKey("sohbet.Message", on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField("neden", max_length=12, choices=Reason.choices)
    detail = models.TextField("açıklama", max_length=1000, blank=True)
    # Şikayet edilen içeriğin o anki kopyası: içerik silinse bile moderatör
    # değerlendirebilsin. Yalnızca şikayet edilen içerik kopyalanır.
    content_snapshot = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    moderator_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "-created_at"]
        verbose_name = "şikayet"
        verbose_name_plural = "şikayetler"
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.get_target_type_display()} · {self.get_reason_display()}"
