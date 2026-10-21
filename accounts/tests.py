import json

from django.urls import reverse

from accounts.models import ConsentRecord, User
from core.testing import PASSWORD, BaseTestCase, make_dert, make_user
from dertler.models import Dert, Reaction
from sohbet.services import send_message, start_conversation


class RegisterTests(BaseTestCase):
    url = reverse("accounts:register")

    def payload(self, **overrides):
        data = {
            "username": "NeşeliPenguen42",
            "password1": PASSWORD,
            "password2": PASSWORD,
            "is_adult": "on",
            "accept_terms": "on",
        }
        data.update(overrides)
        return data

    def test_register_success_records_terms_but_not_special_consent(self):
        response = self.client.post(self.url, self.payload())
        self.assertRedirects(response, reverse("accounts:consent"))
        user = User.objects.get(username="NeşeliPenguen42")
        self.assertTrue(ConsentRecord.objects.filter(user=user, kind="terms").exists())
        self.assertFalse(user.has_special_consent)  # açık rıza ayrı bir adımdır

    def test_adult_and_terms_are_required(self):
        data = self.payload()
        del data["is_adult"]
        del data["accept_terms"]
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_reserved_and_invalid_nicknames(self):
        for nick in ("Moderatör", "admin", "a", "kötü isim", "Привет"):
            response = self.client.post(self.url, self.payload(username=nick))
            self.assertEqual(response.status_code, 200, nick)
        self.assertFalse(User.objects.exists())

    def test_nickname_unique_case_insensitive(self):
        make_user("Kedi_Sever")
        self.client.post(self.url, self.payload(username="kedi_sever"))
        self.assertEqual(User.objects.count(), 1)


class LoginTests(BaseTestCase):
    def test_lockout_after_repeated_failures(self):
        make_user("Sakin_Baykus")
        url = reverse("accounts:login")
        for _ in range(5):
            self.client.post(url, {"username": "Sakin_Baykus", "password": "yanlis-parola"})
        response = self.client.post(url, {"username": "Sakin_Baykus", "password": PASSWORD})
        self.assertContains(response, "çok fazla hatalı deneme")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        user = make_user("Sakin_Baykus")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)


class ConsentTests(BaseTestCase):
    def test_special_consent_required_before_posting(self):
        user = make_user("Rizasiz", consent=False)
        self.client.force_login(user)
        response = self.client.get(reverse("dertler:create"))
        self.assertRedirects(response, reverse("accounts:consent") + "?next=%2Fdertler%2Fanlat%2F")

    def test_give_consent(self):
        user = make_user("Rizasiz", consent=False)
        self.client.force_login(user)
        self.client.post(reverse("accounts:consent"), {"consent": "on"})
        user.refresh_from_db()
        self.assertTrue(user.has_special_consent)

    def test_withdraw_deletes_consent_based_data(self):
        user = make_user("Geri_Alan")
        other = make_user("Diger_Kisi")
        make_dert(user)
        other_dert = make_dert(other, title="Başka bir dert örneği")
        Reaction.objects.create(dert=other_dert, user=user, kind="metoo")
        Reaction.objects.create(dert=other_dert, user=user, kind="hug")
        conv = start_conversation(user, other, other_dert, "Merhaba, dertleşelim mi?")
        conv.status = "active"
        conv.save()
        send_message(conv, user, "Benim mesajım")
        send_message(conv, other, "Onun mesajı")

        self.client.force_login(user)
        self.client.post(reverse("accounts:withdraw_consent"), {"password": PASSWORD})

        user.refresh_from_db()
        conv.refresh_from_db()
        self.assertFalse(user.has_special_consent)
        self.assertFalse(Dert.objects.filter(author=user).exists())
        self.assertFalse(Reaction.objects.filter(user=user, kind="metoo").exists())
        self.assertTrue(Reaction.objects.filter(user=user, kind="hug").exists())
        self.assertFalse(conv.messages.filter(sender=user).exists())
        self.assertEqual(conv.status, "closed")
        self.assertEqual(conv.intro, "")


class DataRightsTests(BaseTestCase):
    def test_export_contains_only_own_messages(self):
        user = make_user("Indiren")
        other = make_user("Karsi_Taraf")
        dert = make_dert(other)
        conv = start_conversation(user, other, dert, "Merhaba, dertleşelim mi?")
        conv.status = "active"
        conv.save()
        send_message(conv, user, "BENIM_GIZLI_MESAJIM")
        send_message(conv, other, "ONUN_GIZLI_MESAJI")

        self.client.force_login(user)
        response = self.client.get(reverse("accounts:export"))
        self.assertEqual(response["Content-Type"], "application/json; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])
        data = json.loads(response.content)
        dump = json.dumps(data, ensure_ascii=False)
        self.assertIn("BENIM_GIZLI_MESAJIM", dump)
        self.assertNotIn("ONUN_GIZLI_MESAJI", dump)
        self.assertEqual(data["hesap"]["rumuz"], "Indiren")

    def test_delete_account_requires_password(self):
        user = make_user("Silinecek")
        make_dert(user)
        self.client.force_login(user)
        url = reverse("accounts:delete")
        self.client.post(url, {"password": "yanlis", "confirm": "on"})
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.client.post(url, {"password": PASSWORD, "confirm": "on"})
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(Dert.objects.exists())
