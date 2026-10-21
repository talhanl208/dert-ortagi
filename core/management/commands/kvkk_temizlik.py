"""
Saklama ve imha politikası: süresi dolan verileri siler.

Canlı ortamda günde bir kez zamanlanmış görev (cron, systemd timer) ile
çalıştırılması önerilir:

    python manage.py kvkk_temizlik            # sil
    python manage.py kvkk_temizlik --dry-run  # yalnızca say
"""

import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from dertler.models import Dert
from guvenlik.models import Report
from sohbet.models import Conversation


class Command(BaseCommand):
    help = "KVKK saklama sürelerini aşan verileri siler."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Silmeden yalnızca kaç kayıt olduğunu göster.")

    def handle(self, *args, dry_run=False, **options):
        now = timezone.now()
        days = settings.RETENTION_DAYS

        def before(key):
            return now - datetime.timedelta(days=days[key])

        User = get_user_model()
        plan = [
            (
                "Kapanmış/reddedilmiş eski sohbetler",
                Conversation.objects.filter(
                    status__in=[Conversation.Status.CLOSED, Conversation.Status.DECLINED],
                    updated_at__lt=before("closed_conversations"),
                ),
            ),
            (
                "Sonuçlanmış eski şikayetler",
                Report.objects.exclude(status=Report.Status.OPEN).filter(reviewed_at__lt=before("resolved_reports")),
            ),
            (
                "Moderasyonla gizlenmiş eski dertler",
                Dert.objects.filter(is_hidden=True, updated_at__lt=before("hidden_dertler")),
            ),
            (
                "Uzun süredir kullanılmayan hesaplar",
                User.objects.filter(is_staff=False, is_superuser=False).filter(
                    Q(last_login__lt=before("inactive_accounts"))
                    | Q(last_login__isnull=True, date_joined__lt=before("inactive_accounts"))
                ),
            ),
        ]

        with transaction.atomic():
            for label, qs in plan:
                count = qs.count()
                if not dry_run and count:
                    qs.delete()
                verb = "silinecek" if dry_run else "silindi"
                self.stdout.write(f"{label}: {count} kayıt {verb}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Deneme modu: hiçbir şey silinmedi."))
        else:
            self.stdout.write(self.style.SUCCESS("Temizlik tamamlandı."))
