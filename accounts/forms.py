from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from core.ratelimit import hit, is_limited, username_key
from dertler.models import Category

from .models import AVATAR_CHOICES, User

LOGIN_FAIL_LIMIT = 5
LOGIN_FAIL_WINDOW = 15 * 60


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label="E-posta (isteğe bağlı)",
        required=False,
        help_text="Yalnızca parolanı unutursan kullanılır. Kimseye gösterilmez.",
    )
    is_adult = forms.BooleanField(
        label="18 yaşından büyüğüm.",
        error_messages={"required": "Dert Ortağı yalnızca 18 yaş ve üzeri içindir."},
    )
    accept_terms = forms.BooleanField(
        label="Kullanım Koşulları'nı ve Topluluk Kuralları'nı okudum, kabul ediyorum.",
        error_messages={"required": "Devam etmek için kullanım koşullarını kabul etmelisin."},
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
        labels = {"username": "Rumuz"}
        help_texts = {
            "username": "Gerçek adını kullanma. Herkes seni bu rumuzla görür.",
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            # Hesap varlığını sızdırmamak için genel bir ifade kullan.
            raise ValidationError("Bu e-posta adresi kullanılamıyor.")
        return email


class LoginForm(AuthenticationForm):
    """Aynı rumuz için art arda hatalı denemelerde geçici kilit."""

    def clean(self):
        username = self.cleaned_data.get("username") or ""
        key = username_key(username)
        if is_limited("login-fail", key, LOGIN_FAIL_LIMIT, LOGIN_FAIL_WINDOW):
            raise ValidationError(
                "Bu hesap için çok fazla hatalı deneme yapıldı. 15 dakika sonra tekrar dene.",
                code="locked",
            )
        try:
            return super().clean()
        except ValidationError:
            hit("login-fail", key, LOGIN_FAIL_LIMIT, LOGIN_FAIL_WINDOW)
            raise


class SettingsForm(forms.ModelForm):
    avatar = forms.ChoiceField(
        label="Avatarın",
        choices=AVATAR_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "avatar-picker"}),
    )
    listener_categories = forms.ModelMultipleChoiceField(
        label="Hangi konularda dinlemek istersin?",
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = User
        fields = ("avatar", "email", "is_listener", "listener_categories")
        labels = {"email": "E-posta (isteğe bağlı)"}

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Bu e-posta adresi kullanılamıyor.")
        return email


class SpecialConsentForm(forms.Form):
    consent = forms.BooleanField(
        label=(
            "Açık Rıza Metni'ni okudum. Paylaşacağım dertler ve mesajlarda yer "
            "alabilecek sağlık ve diğer özel nitelikli kişisel verilerimin bu "
            "metinde açıklanan amaçlarla işlenmesine açık rıza veriyorum."
        ),
        error_messages={"required": "Devam etmek için kutucuğu işaretlemelisin."},
    )


class PasswordConfirmForm(forms.Form):
    password = forms.CharField(
        label="Parolan",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        key = f"u:{self.user.pk}"
        if is_limited("password-confirm", key, LOGIN_FAIL_LIMIT, LOGIN_FAIL_WINDOW):
            raise ValidationError("Çok fazla hatalı deneme. Biraz sonra tekrar dene.")
        if not self.user.check_password(password):
            hit("password-confirm", key, LOGIN_FAIL_LIMIT, LOGIN_FAIL_WINDOW)
            raise ValidationError("Parola doğru değil.")
        return password


class DeleteAccountForm(PasswordConfirmForm):
    confirm = forms.BooleanField(
        label="Hesabımın ve tüm verilerimin kalıcı olarak silineceğini anladım.",
    )
