import secrets
import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

# Profil fotoğrafı yerine emoji avatar: hem neşeli hem de kişisel veri
# (yüz görüntüsü) toplamıyoruz.
AVATAR_CHOICES = [
    ("🦊", "Tilki"),
    ("🐼", "Panda"),
    ("🐨", "Koala"),
    ("🐯", "Kaplan"),
    ("🦁", "Aslan"),
    ("🐸", "Kurbağa"),
    ("🐙", "Ahtapot"),
    ("🦄", "Tekboynuz"),
    ("🐝", "Arı"),
    ("🐢", "Kaplumbağa"),
    ("🦉", "Baykuş"),
    ("🐧", "Penguen"),
    ("🐰", "Tavşan"),
    ("🐻", "Ayı"),
    ("🐳", "Balina"),
    ("🦋", "Kelebek"),
    ("🐱", "Kedi"),
    ("🌻", "Ayçiçeği"),
]

NICK_ADJECTIVES = [
    "Neşeli",
    "Güleç",
    "Umutlu",
    "Sakin",
    "Cesur",
    "Şirin",
    "Meraklı",
    "Tatlı",
    "Güneşli",
    "Sevimli",
    "Yumuşak",
    "Uykucu",
    "Hayalperest",
    "Pofuduk",
]

RESERVED_NICKS = {
    "admin",
    "administrator",
    "yonetici",
    "yönetici",
    "moderator",
    "moderatör",
    "moderasyon",
    "dertortagi",
    "dertortağı",
    "destek",
    "sistem",
    "anonim",
    "root",
    "staff",
    "yetkili",
    "resmi",
}

username_validator = RegexValidator(
    r"^[A-Za-z0-9_çğıöşüÇĞİÖŞÜ]{3,24}$",
    "Rumuz 3–24 karakter olmalı. Harf, rakam ve alt çizgi kullanabilirsin.",
)


def validate_not_reserved(value: str):
    from core.text import normalize

    plain = normalize(value).replace("_", "")
    if plain in {normalize(n) for n in RESERVED_NICKS}:
        raise ValidationError("Bu rumuz ayrılmış, başka bir tane seçer misin?")


def random_avatar() -> str:
    return secrets.choice(AVATAR_CHOICES)[0]


def suggest_nickname() -> str:
    animal = secrets.choice(AVATAR_CHOICES)[1]
    adjective = secrets.choice(NICK_ADJECTIVES)
    return f"{adjective}{animal}{10 + secrets.randbelow(90)}"


class DertUserManager(UserManager):
    pass


class User(AbstractUser):
    # Veri minimizasyonu: gerçek ad-soyad toplanmaz.
    first_name = None
    last_name = None

    username = models.CharField(
        "rumuz",
        max_length=24,
        unique=True,
        validators=[username_validator, validate_not_reserved],
        error_messages={"unique": "Bu rumuz alınmış, başka bir tane dener misin?"},
    )
    email = models.EmailField(
        "e-posta",
        blank=True,
        help_text="İsteğe bağlı. Yalnızca parola sıfırlamak için kullanılır, kimseye gösterilmez.",
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    avatar = models.CharField("avatar", max_length=8, choices=AVATAR_CHOICES, default=random_avatar)

    is_listener = models.BooleanField(
        "dinleyici gönüllüsüyüm",
        default=False,
        help_text="Dinlenmeyi bekleyen dertleri görür, istersen dert ortağı olursun.",
    )
    listener_categories = models.ManyToManyField(
        "dertler.Category", blank=True, related_name="listeners", verbose_name="dinlemek istediğim konular"
    )

    terms_version = models.CharField(max_length=10, blank=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    special_consent_version = models.CharField(max_length=10, blank=True)
    special_consent_at = models.DateTimeField(null=True, blank=True)

    REQUIRED_FIELDS = []
    objects = DertUserManager()

    class Meta:
        verbose_name = "kullanıcı"
        verbose_name_plural = "kullanıcılar"
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="unique_nonempty_email_ci",
                violation_error_message="Bu e-posta başka bir hesapta kayıtlı.",
            )
        ]

    def __str__(self):
        return self.username

    @property
    def has_special_consent(self) -> bool:
        return self.special_consent_at is not None


class ConsentRecord(models.Model):
    """Rıza ve onay geçmişi: kim, hangi metnin hangi sürümünü, ne zaman."""

    class Kind(models.TextChoices):
        TERMS = "terms", "Kullanım koşulları"
        SPECIAL_DATA = "special_data", "Özel nitelikli veri açık rızası"

    class Action(models.TextChoices):
        GIVEN = "given", "Verildi"
        WITHDRAWN = "withdrawn", "Geri alındı"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    action = models.CharField(max_length=10, choices=Action.choices)
    version = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "rıza kaydı"
        verbose_name_plural = "rıza kayıtları"

    def __str__(self):
        return f"{self.user} · {self.get_kind_display()} · {self.get_action_display()}"
