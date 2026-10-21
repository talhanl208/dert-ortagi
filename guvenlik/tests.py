from django.test import override_settings
from django.urls import reverse

from core.testing import BaseTestCase, make_dert, make_user
from dertler.models import Dert
from guvenlik.models import Block, Report
from sohbet.services import send_message, start_conversation


class ReportTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("Dert_Sahibi")
        self.dert = make_dert(self.owner)

    def report(self, user, **extra):
        self.client.force_login(user)
        data = {"reason": "harassment", "detail": ""}
        data.update(extra)
        return self.client.post(reverse("guvenlik:report", args=["dert", self.dert.public_id]), data)

    @override_settings(AUTO_HIDE_REPORT_THRESHOLD=3)
    def test_auto_hide_after_distinct_reporters(self):
        reporters = [make_user(f"Bildiren_{i}") for i in range(3)]
        self.report(reporters[0])
        self.report(reporters[0])  # aynı kişinin ikinci şikayeti sayılmaz
        self.dert.refresh_from_db()
        self.assertFalse(self.dert.is_hidden)
        self.report(reporters[1])
        self.report(reporters[2])
        self.dert.refresh_from_db()
        self.assertTrue(self.dert.is_hidden)
        self.assertEqual(Report.objects.count(), 3)

    def test_snapshot_is_saved(self):
        self.report(make_user("Bildiren"))
        self.assertIn(self.dert.summary, Report.objects.get().content_snapshot)

    def test_report_and_block(self):
        reporter = make_user("Bildiren")
        self.report(reporter, also_block="on")
        self.assertTrue(Block.objects.filter(blocker=reporter, blocked=self.owner).exists())

    def test_cannot_report_own_dert(self):
        self.client.force_login(self.owner)
        url = reverse("guvenlik:report", args=["dert", self.dert.public_id])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_only_participants_can_report_messages(self):
        helper = make_user("Yardimci")
        conv = start_conversation(helper, self.owner, self.dert, "Merhaba, dertleşelim mi?")
        conv.status = "active"
        conv.save()
        msg = send_message(conv, self.owner, "kaba bir mesaj")
        url = reverse("guvenlik:report", args=["mesaj", msg.public_id])

        self.client.force_login(make_user("Yabanci"))
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)  # kendi mesajını şikayet edemez
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(helper)
        self.client.post(url, {"reason": "harassment"})
        self.assertEqual(Report.objects.get().content_snapshot, "kaba bir mesaj")


class BlockTests(BaseTestCase):
    def test_block_hides_dertler_both_ways(self):
        a = make_user("Kisi_A")
        b = make_user("Kisi_B")
        dert_a = make_dert(a, title="A kişisinin derdi burada")
        dert_b = make_dert(b, title="B kişisinin derdi burada")
        self.client.force_login(a)
        self.client.post(reverse("guvenlik:block", args=["dert", dert_b.public_id]))
        self.assertNotContains(self.client.get(reverse("dertler:list")), "B kişisinin derdi")
        self.assertEqual(self.client.get(dert_b.get_absolute_url()).status_code, 404)

        self.client.force_login(b)
        self.assertNotContains(self.client.get(reverse("dertler:list")), "A kişisinin derdi")
        self.assertEqual(self.client.get(dert_a.get_absolute_url()).status_code, 404)

    def test_blocking_anonymous_author_keeps_label_anonymous(self):
        a = make_user("Kisi_A")
        b = make_user("Gizli_Kisi")
        dert = make_dert(b, is_anonymous=True)
        self.client.force_login(a)
        self.client.post(reverse("guvenlik:block", args=["dert", dert.public_id]))
        response = self.client.get(reverse("guvenlik:blocked"))
        self.assertContains(response, "Anonim dert ortağı")
        self.assertNotContains(response, "Gizli_Kisi")

    def test_unblock_only_own_blocks(self):
        a = make_user("Kisi_A")
        b = make_user("Kisi_B")
        c = make_user("Kisi_C")
        block = Block.objects.create(blocker=a, blocked=b, label="Kisi_B")
        self.client.force_login(c)
        self.client.post(reverse("guvenlik:unblock", args=[block.pk]))
        self.assertTrue(Block.objects.filter(pk=block.pk).exists())
        self.client.force_login(a)
        self.client.post(reverse("guvenlik:unblock", args=[block.pk]))
        self.assertFalse(Block.objects.filter(pk=block.pk).exists())


class RetentionCommandTests(BaseTestCase):
    def test_cleanup_removes_old_closed_conversations(self):
        import datetime
        from io import StringIO

        from django.core.management import call_command
        from django.utils import timezone

        from sohbet.models import Conversation

        a = make_user("Kisi_A")
        b = make_user("Kisi_B")
        dert = make_dert(b)
        conv = start_conversation(a, b, dert, "Merhaba, dertleşelim mi?")
        old = timezone.now() - datetime.timedelta(days=400)
        Conversation.objects.filter(pk=conv.pk).update(status="closed", updated_at=old)
        Dert.objects.filter(pk=dert.pk).update(is_hidden=True, updated_at=old)

        out = StringIO()
        call_command("kvkk_temizlik", "--dry-run", stdout=out)
        self.assertTrue(Conversation.objects.exists())
        call_command("kvkk_temizlik", stdout=out)
        self.assertFalse(Conversation.objects.exists())
        self.assertFalse(Dert.objects.exists())
