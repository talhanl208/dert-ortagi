import uuid

from django.conf import settings
from django.db import models
from django.db.models import Count, Q
from django.urls import reverse


class Category(models.Model):
    class Color(models.TextChoices):
        SUN = "sun", "Ayçiçeği sarısı"
        TURQ = "turq", "Çini turkuazı"
        ROSE = "rose", "Nar çiçeği"
        LEAF = "leaf", "Yaprak yeşili"
        LILAC = "lilac", "Leylak"
        SKY = "sky", "Gökyüzü"

    name = models.CharField("ad", max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True)
    emoji = models.CharField(max_length=8)
    color = models.CharField(max_length=8, choices=Color.choices, default=Color.SUN)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "kategori"
        verbose_name_plural = "kategoriler"

    def __str__(self):
        return f"{self.emoji} {self.name}"


class DertQuerySet(models.QuerySet):
    def public(self):
        return self.filter(is_hidden=False)

    def visible_to(self, user):
        """Gizlenmiş dertleri ve engelleme ilişkisi olan kişilerin dertlerini çıkarır."""
        qs = self.public().filter(author__is_active=True)  # askıya alınan hesapların dertleri görünmez
        if user is not None and user.is_authenticated:
            from guvenlik.models import Block

            qs = qs.exclude(author_id__in=Block.objects.related_user_ids(user))
        return qs

    def with_counts(self):
        return self.annotate(
            hug_count=Count("reactions", filter=Q(reactions__kind=Reaction.Kind.HUG), distinct=True),
            strength_count=Count("reactions", filter=Q(reactions__kind=Reaction.Kind.STRENGTH), distinct=True),
            metoo_count=Count("reactions", filter=Q(reactions__kind=Reaction.Kind.METOO), distinct=True),
        )


class Dert(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Paylaşıldı"
        LIGHTER = "lighter", "Hafifledi"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dertler")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="dertler", verbose_name="kategori")
    title = models.CharField("başlık", max_length=120)
    summary = models.TextField("kısa özet", max_length=1500)
    is_anonymous = models.BooleanField(
        "rumuzumu gizle",
        default=False,
        help_text="Dertte rumuzun yerine 'Anonim dert ortağı' yazar.",
    )
    open_to_chat = models.BooleanField(
        "sohbet isteklerine açığım",
        default=True,
        help_text="Başkaları sana sohbet isteği gönderebilir. Kabul etmeden kimse yazamaz.",
    )
    show_to_listeners = models.BooleanField(
        "dinleyici gönüllülerine de göster",
        default=True,
        help_text="Bu konuyu dinlemeye gönüllü olan kişilerin listesinde görünür.",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    is_hidden = models.BooleanField("gizlendi (moderasyon)", default=False)
    hidden_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DertQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "dert"
        verbose_name_plural = "dertler"
        indexes = [models.Index(fields=["is_hidden", "-created_at"])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("dertler:detail", args=[self.public_id])

    @property
    def display_name(self):
        return "Anonim dert ortağı" if self.is_anonymous else self.author.username

    @property
    def display_avatar(self):
        return "🫖" if self.is_anonymous else self.author.avatar


class Reaction(models.Model):
    class Kind(models.TextChoices):
        HUG = "hug", "Sarıl"
        STRENGTH = "strength", "Güç gönder"
        METOO = "metoo", "Ben de yaşıyorum"

    dert = models.ForeignKey(Dert, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reactions")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "tepki"
        verbose_name_plural = "tepkiler"
        constraints = [
            models.UniqueConstraint(fields=["dert", "user", "kind"], name="one_reaction_kind_per_user"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.dert_id}"
