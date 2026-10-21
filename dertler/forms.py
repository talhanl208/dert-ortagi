from django import forms
from django.core.exceptions import ValidationError

from core.text import find_contact_info

from .models import Category, Dert


class CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj


class DertForm(forms.ModelForm):
    category = CategoryChoiceField(
        label="Derdin hangi konuyla ilgili?",
        queryset=Category.objects.all(),
        widget=forms.RadioSelect,
        empty_label=None,
        error_messages={"required": "Bir kategori seç ki benzer dertte olanlar seni bulabilsin."},
    )

    class Meta:
        model = Dert
        fields = ("category", "title", "summary", "is_anonymous", "open_to_chat", "show_to_listeners")
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Ör. Sınav kaygısı uykumu kaçırıyor",
                    "maxlength": 120,
                    "data-counter": "120",
                }
            ),
            "summary": forms.Textarea(
                attrs={
                    "rows": 7,
                    "placeholder": "Ne oluyor, nasıl hissediyorsun? İstediğin kadarını anlat.",
                    "maxlength": 1500,
                    "data-counter": "1500",
                }
            ),
        }
        labels = {"title": "Başlık", "summary": "Kısa özet"}

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 5:
            raise ValidationError("Başlık en az 5 karakter olsun.")
        return title

    def clean_summary(self):
        summary = self.cleaned_data["summary"].strip()
        if len(summary) < 20:
            raise ValidationError("Biraz daha anlatır mısın? En az 20 karakter yeterli.")
        return summary

    def clean(self):
        cleaned = super().clean()
        found = find_contact_info(f"{cleaned.get('title', '')} {cleaned.get('summary', '')}")
        if found:
            raise ValidationError(
                f"Güvenliğin için herkese açık dertlerde iletişim bilgisi paylaşma (bulunan: {', '.join(found)})."
            )
        return cleaned


class FilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=80)
    kategori = forms.SlugField(required=False, max_length=40)
