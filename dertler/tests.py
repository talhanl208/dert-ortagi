from django.urls import reverse

from core.testing import BaseTestCase, make_dert, make_user
from dertler.models import Category, Dert, Reaction


class DertCreateTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("Yazan_Kisi")
        self.client.force_login(self.user)
        self.url = reverse("dertler:create")
        self.category = Category.objects.get(slug="yalnizlik")

    def post(self, follow=False, **overrides):
        data = {
            "category": self.category.pk,
            "title": "Yeni şehirde yalnızım",
            "summary": "Taşındım ve hafta sonları kimseyle konuşmuyorum, çok sessiz geçiyor.",
            "open_to_chat": "on",
        }
        data.update(overrides)
        return self.client.post(self.url, data, follow=follow)

    def test_create(self):
        response = self.post()
        dert = Dert.objects.get()
        self.assertRedirects(response, dert.get_absolute_url())
        self.assertEqual(dert.author, self.user)

    def test_contact_info_is_rejected(self):
        response = self.post(summary="Bana yazın: 0532 123 45 67 numaramdan ulaşabilirsiniz.")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "iletişim bilgisi paylaşma")
        self.assertFalse(Dert.objects.exists())

    def test_crisis_text_shows_support_lines(self):
        response = self.post(summary="Bazen yaşamak istemiyorum diye düşünüyorum, çok yoruldum.", follow=True)
        self.assertContains(response, "ALO 183")

    def test_html_is_escaped(self):
        self.post(title="<script>alert(1)</script> başlık")
        dert = Dert.objects.get()
        response = self.client.get(dert.get_absolute_url())
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")


class DertVisibilityTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("Dert_Sahibi")
        self.other = make_user("Okuyan_Kisi")

    def test_anonymous_dert_hides_author(self):
        dert = make_dert(self.owner, is_anonymous=True)
        self.client.force_login(self.other)
        for url in (dert.get_absolute_url(), reverse("dertler:list"), reverse("core:home")):
            response = self.client.get(url)
            self.assertNotContains(response, "Dert_Sahibi")
            self.assertNotContains(response, str(self.owner.public_id))

    def test_hidden_dert_only_visible_to_owner(self):
        dert = make_dert(self.owner, is_hidden=True)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(dert.get_absolute_url()).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(dert.get_absolute_url()).status_code, 200)

    def test_suspended_users_dertler_are_hidden(self):
        dert = make_dert(self.owner, title="Askıya alınan kişinin derdi")
        self.owner.is_active = False
        self.owner.save()
        self.assertNotContains(self.client.get(reverse("dertler:list")), "Askıya alınan kişinin derdi")
        self.assertFalse(Dert.objects.visible_to(self.other).filter(pk=dert.pk).exists())

    def test_cannot_edit_or_delete_others_dert(self):
        dert = make_dert(self.owner)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("dertler:edit", args=[dert.public_id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("dertler:delete", args=[dert.public_id])).status_code, 404)
        self.assertTrue(Dert.objects.filter(pk=dert.pk).exists())

    def test_delete_requires_post(self):
        dert = make_dert(self.owner)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("dertler:delete", args=[dert.public_id])).status_code, 405)


class ReactionTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("Dert_Sahibi")
        self.dert = make_dert(self.owner)
        self.url = reverse("dertler:react", args=[self.dert.public_id])

    def test_toggle_hug(self):
        user = make_user("Sarilan", consent=False)
        self.client.force_login(user)
        self.client.post(self.url, {"kind": "hug"})
        self.assertEqual(Reaction.objects.count(), 1)
        self.client.post(self.url, {"kind": "hug"})
        self.assertEqual(Reaction.objects.count(), 0)

    def test_metoo_requires_special_consent(self):
        user = make_user("Rizasiz", consent=False)
        self.client.force_login(user)
        response = self.client.post(self.url, {"kind": "metoo"})
        self.assertTrue(response["Location"].startswith(reverse("accounts:consent")))
        self.assertFalse(Reaction.objects.exists())

    def test_cannot_react_to_own_dert(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, {"kind": "hug"})
        self.assertFalse(Reaction.objects.exists())

    def test_invalid_kind(self):
        self.client.force_login(make_user("Herhangi"))
        self.assertEqual(self.client.post(self.url, {"kind": "kotu"}).status_code, 404)


class MatchingTests(BaseTestCase):
    def test_similar_dertler_prefers_overlap(self):
        from dertler.matching import similar_dertler

        a = make_user("Kisi_A")
        b = make_user("Kisi_B")
        c = make_user("Kisi_C")
        base = make_dert(a, title="Sınav kaygısı yüzünden uyuyamıyorum")
        close = make_dert(b, title="Sınav öncesi kaygı ve uykusuzluk")
        make_dert(c, title="Ders seçimi konusunda kararsızım", summary="Hangi seçmeli dersi alacağımı bilmiyorum.")
        result = similar_dertler(base, a, limit=2)
        self.assertEqual(result[0], close)
