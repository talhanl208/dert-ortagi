from django import forms

from .models import Report


class ReportForm(forms.Form):
    reason = forms.ChoiceField(
        label="Neden şikayet ediyorsun?",
        choices=Report.Reason.choices,
        widget=forms.RadioSelect,
    )
    detail = forms.CharField(
        label="Eklemek istediğin bir şey var mı? (isteğe bağlı)",
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 1000, "data-counter": "1000"}),
    )
    also_block = forms.BooleanField(
        label="Bu kişiyi engelle, bana bir daha ulaşamasın.",
        required=False,
        initial=True,
    )
