from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def once(value):
    """'3 saat önce' gibi göreli zaman; bir dakikadan yeniyse 'az önce'."""
    if not value:
        return ""
    if (timezone.now() - value).total_seconds() < 60:
        return "az önce"
    return f"{timesince(value, depth=1)} önce"
