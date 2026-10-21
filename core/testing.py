"""Testler için ortak yardımcılar."""

import secrets

from django.core.cache import cache
from django.test import TestCase

from accounts.models import User
from accounts.services import give_special_consent, record_terms_acceptance
from dertler.models import Category, Dert

# Her test çalıştırmasında rastgele üretilir; depoda sabit parola tutulmaz.
PASSWORD = secrets.token_urlsafe(16)


def make_user(username, consent=True, **extra):
    user = User.objects.create_user(username=username, password=PASSWORD, **extra)
    record_terms_acceptance(user)
    if consent:
        give_special_consent(user)
    return user


def make_dert(author, title="Sınav kaygısı uykumu kaçırıyor", **extra):
    defaults = {
        "summary": "Sınavdan önceki gece hiç uyuyamıyorum ve sabah çok yorgun oluyorum.",
        "category": Category.objects.get(slug="okul-sinavlar"),
    }
    defaults.update(extra)
    return Dert.objects.create(author=author, title=title, **defaults)


class BaseTestCase(TestCase):
    def setUp(self):
        cache.clear()  # hız sınırı sayaçları testler arasında taşınmasın
