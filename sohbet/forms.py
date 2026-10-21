from django import forms
from django.core.exceptions import ValidationError


class RequestForm(forms.Form):
    intro = forms.CharField(
        label="Kendini kısaca tanıt",
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "maxlength": 500,
                "data-counter": "500",
                "placeholder": "Ör. Merhaba, ben de benzer bir dönemden geçtim. İstersen dertleşelim.",
            }
        ),
    )

    def clean_intro(self):
        intro = self.cleaned_data["intro"].strip()
        if len(intro) < 10:
            raise ValidationError("Birkaç kelimeyle kendini tanıt, en az 10 karakter.")
        return intro


class MessageForm(forms.Form):
    body = forms.CharField(
        label="Mesajın",
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "maxlength": 1000,
                "placeholder": "Bir şeyler yaz…",
                "autocomplete": "off",
            }
        ),
    )

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise ValidationError("Boş mesaj gönderilemez.")
        return body
