"""
Yerelde denemek için örnek kullanıcılar ve dertler oluşturur.
Yalnızca DEBUG modunda çalışır. Parola her çalıştırmada rastgele üretilir
ve yalnızca terminale yazdırılır.
"""

import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.services import give_special_consent, record_terms_acceptance
from dertler.models import Category, Dert, Reaction

SAMPLE = [
    (
        "UmutluPenguen23",
        "🐧",
        "okul-sinavlar",
        "Final haftası geliyor, hiçbir şeye yetişemiyorum",
        "Üç sınavım aynı haftada. Çalışmaya oturunca odaklanamıyorum, sonra da kendime kızıyorum. "
        "Benzer bir şey yaşayan var mı, nasıl baş ettiniz?",
    ),
    (
        "SakinBaykuş41",
        "🦉",
        "yalnizlik",
        "Yeni şehre taşındım, kimseyi tanımıyorum",
        "İş için Sakarya'ya taşındım. Hafta içi idare ediyor ama hafta sonları çok sessiz geçiyor. "
        "Sadece biriyle çay içip sohbet etmek istiyorum.",
    ),
    (
        "CesurAyı77",
        "🐻",
        "is-kariyer",
        "Staj sonrası iş bulamamak moralimi bozuyor",
        "Mezun olalı altı ay oldu. Başvurularıma ya hiç dönüş gelmiyor ya da olumsuz. "
        "Arkadaşlarım tek tek işe başlıyor, ben geride kalmış gibi hissediyorum.",
    ),
    (
        "TatlıKelebek12",
        "🦋",
        "aile",
        "Ailemle sürekli aynı konuda tartışıyoruz",
        "Bölüm seçimim yüzünden her akşam yemekte aynı konuşma dönüyor. Onları kırmak istemiyorum "
        "ama kendi kararımı da vermek istiyorum.",
    ),
    (
        "GüneşliArı58",
        "🐝",
        "okul-sinavlar",
        "Sınav kaygısı yüzünden uyuyamıyorum",
        "Sınavdan önceki gece hiç uyuyamıyorum, sabah da kafam bulanık oluyor. "
        "Çalıştığım her şeyi unutmuş gibi hissediyorum.",
    ),
    (
        "MeraklıTilki90",
        "🦊",
        "gelecek-kaygisi",
        "Doğru bölümde miyim bilmiyorum",
        "Üçüncü sınıftayım ve derslerden zevk almıyorum. Bırakmak da devam etmek de korkutucu geliyor.",
    ),
]


class Command(BaseCommand):
    help = "Yerel geliştirme için örnek veri oluşturur (yalnızca DEBUG)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Bu komut yalnızca DJANGO_DEBUG=True iken çalışır.")
        User = get_user_model()
        password = secrets.token_urlsafe(12)
        users = []
        for nick, avatar, cat_slug, title, summary in SAMPLE:
            user, created = User.objects.get_or_create(username=nick, defaults={"avatar": avatar})
            user.set_password(password)
            user.save()
            if created:
                record_terms_acceptance(user)
                give_special_consent(user)
            users.append(user)
            category = Category.objects.get(slug=cat_slug)
            Dert.objects.get_or_create(author=user, title=title, defaults={"summary": summary, "category": category})

        # Birkaç tepki ve bir dinleyici gönüllüsü
        dertler = list(Dert.objects.all())
        for i, user in enumerate(users):
            for dert in dertler[i % len(dertler) :: 2]:
                if dert.author_id != user.pk:
                    Reaction.objects.get_or_create(dert=dert, user=user, kind=Reaction.Kind.HUG)
        listener = users[1]
        listener.is_listener = True
        listener.save(update_fields=["is_listener"])

        self.stdout.write(self.style.SUCCESS(f"{len(users)} örnek kullanıcı hazır ({timezone.localtime():%H:%M})."))
        self.stdout.write("Rumuzlar: " + ", ".join(u.username for u in users))
        self.stdout.write(f"Hepsinin geçici parolası: {password}")
