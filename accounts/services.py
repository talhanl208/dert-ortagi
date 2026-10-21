"""Hesapla ilgili KVKK işlemleri: rıza verme/geri alma, veri dışa aktarma."""

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import ConsentRecord, User


def record_terms_acceptance(user: User):
    version = settings.LEGAL_VERSIONS["terms"]
    user.terms_version = version
    user.terms_accepted_at = timezone.now()
    user.save(update_fields=["terms_version", "terms_accepted_at"])
    ConsentRecord.objects.create(
        user=user, kind=ConsentRecord.Kind.TERMS, action=ConsentRecord.Action.GIVEN, version=version
    )


def give_special_consent(user: User):
    version = settings.LEGAL_VERSIONS["special_data"]
    user.special_consent_version = version
    user.special_consent_at = timezone.now()
    user.save(update_fields=["special_consent_version", "special_consent_at"])
    ConsentRecord.objects.create(
        user=user,
        kind=ConsentRecord.Kind.SPECIAL_DATA,
        action=ConsentRecord.Action.GIVEN,
        version=version,
    )


@transaction.atomic
def withdraw_special_consent(user: User):
    """
    Açık rıza geri alınınca, rızaya dayanarak işlenen veriler silinir:
    kullanıcının dertleri, "ben de yaşıyorum" tepkileri ve gönderdiği mesajlar.
    Açık sohbetleri kapatılır.
    """
    from dertler.models import Dert, Reaction
    from sohbet.models import Conversation, Message

    Dert.objects.filter(author=user).delete()
    Reaction.objects.filter(user=user, kind=Reaction.Kind.METOO).delete()
    Message.objects.filter(sender=user).delete()
    Conversation.objects.filter(initiator=user).update(intro="")
    Conversation.objects.for_user(user).open().update(status=Conversation.Status.CLOSED, closed_at=timezone.now())

    user.special_consent_version = ""
    user.special_consent_at = None
    user.save(update_fields=["special_consent_version", "special_consent_at"])
    ConsentRecord.objects.create(
        user=user,
        kind=ConsentRecord.Kind.SPECIAL_DATA,
        action=ConsentRecord.Action.WITHDRAWN,
        version=settings.LEGAL_VERSIONS["special_data"],
    )


def _iso(dt):
    return dt.isoformat() if dt else None


def export_user_data(user: User) -> dict:
    """KVKK m.11 kapsamında kullanıcının kendi verilerinin bir kopyası."""
    from dertler.models import Dert, Reaction
    from guvenlik.models import Block, Report
    from sohbet.models import Conversation, Message

    dertler = Dert.objects.filter(author=user).select_related("category")
    conversations = Conversation.objects.for_user(user).select_related("dert", "initiator", "recipient")

    return {
        "aciklama": (
            "Bu dosya Dert Ortağı'nda senin hakkında tutulan verilerin bir kopyasıdır. "
            "Başkalarına ait mesajlar, onların kişisel verisi olduğu için dahil edilmemiştir."
        ),
        "olusturulma_zamani": _iso(timezone.now()),
        "hesap": {
            "rumuz": user.username,
            "e_posta": user.email or None,
            "avatar": user.avatar,
            "kayit_tarihi": _iso(user.date_joined),
            "son_giris": _iso(user.last_login),
            "dinleyici_gonullusu": user.is_listener,
            "dinlenen_konular": [c.name for c in user.listener_categories.all()],
        },
        "rizalar": [
            {
                "tur": c.get_kind_display(),
                "islem": c.get_action_display(),
                "surum": c.version,
                "zaman": _iso(c.created_at),
            }
            for c in user.consents.all()
        ],
        "dertler": [
            {
                "baslik": d.title,
                "ozet": d.summary,
                "kategori": d.category.name,
                "anonim": d.is_anonymous,
                "sohbete_acik": d.open_to_chat,
                "durum": d.get_status_display(),
                "olusturulma": _iso(d.created_at),
            }
            for d in dertler
        ],
        "tepkiler": [
            {"dert": r.dert.title, "tepki": r.get_kind_display(), "zaman": _iso(r.created_at)}
            for r in Reaction.objects.filter(user=user).select_related("dert")
        ],
        "sohbetler": [
            {
                "karsi_taraf": c.other_display(user)["name"],
                "dert": c.dert.title if c.dert else None,
                "durum": c.get_status_display(),
                "baslangic": _iso(c.created_at),
                "istek_mesajim": c.intro if c.initiator_id == user.pk else None,
                "mesajlarim": [
                    {"metin": m.body, "zaman": _iso(m.created_at)}
                    for m in Message.objects.filter(conversation=c, sender=user)
                ],
            }
            for c in conversations
        ],
        "engellediklerim": [b.blocked.username for b in Block.objects.filter(blocker=user).select_related("blocked")],
        "sikayetlerim": [
            {"neden": r.get_reason_display(), "durum": r.get_status_display(), "zaman": _iso(r.created_at)}
            for r in Report.objects.filter(reporter=user)
        ],
    }
