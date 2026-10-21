from django.urls import reverse

from core.testing import BaseTestCase, make_dert, make_user
from dertler.models import Reaction
from guvenlik.services import block_user
from sohbet.models import Conversation, Message
from sohbet.services import ChatError, send_message, start_conversation


class ChatFlowTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("Dert_Sahibi")
        self.helper = make_user("Dert_Ortagi")
        self.stranger = make_user("Yabanci")
        self.dert = make_dert(self.owner)

    def request_chat(self):
        self.client.force_login(self.helper)
        self.client.post(
            reverse("sohbet:request", args=[self.dert.public_id]),
            {"intro": "Merhaba, ben de benzer bir şey yaşadım."},
        )
        return Conversation.objects.get()

    def test_request_then_accept_then_message(self):
        conv = self.request_chat()
        self.assertEqual(conv.status, "pending")

        # Kabul edilmeden mesaj gönderilemez
        self.client.post(reverse("sohbet:send", args=[conv.public_id]), {"body": "Selam?"})
        self.assertFalse(Message.objects.exists())

        # İsteği yalnızca alıcı kabul edebilir
        self.assertEqual(self.client.post(reverse("sohbet:accept", args=[conv.public_id])).status_code, 404)
        self.client.force_login(self.owner)
        self.client.post(reverse("sohbet:accept", args=[conv.public_id]))
        conv.refresh_from_db()
        self.assertEqual(conv.status, "active")

        self.client.post(reverse("sohbet:send", args=[conv.public_id]), {"body": "Hoş geldin!"})
        self.assertEqual(Message.objects.get().body, "Hoş geldin!")

    def test_non_participant_gets_404_everywhere(self):
        conv = self.request_chat()
        self.client.force_login(self.stranger)
        for name in ("detail", "poll"):
            self.assertEqual(self.client.get(reverse(f"sohbet:{name}", args=[conv.public_id])).status_code, 404)
        for name in ("send", "accept", "decline", "close"):
            self.assertEqual(self.client.post(reverse(f"sohbet:{name}", args=[conv.public_id])).status_code, 404)

    def test_poll_returns_json_and_only_new_messages(self):
        conv = start_conversation(self.helper, self.owner, self.dert, "Merhaba, dertleşelim mi?")
        conv.status = "active"
        conv.save()
        first = send_message(conv, self.owner, "<b>ilk</b>")
        send_message(conv, self.helper, "ikinci")
        self.client.force_login(self.helper)
        response = self.client.get(reverse("sohbet:poll", args=[conv.public_id]), {"after": first.pk})
        data = response.json()
        self.assertEqual([m["body"] for m in data["messages"]], ["ikinci"])
        self.assertTrue(data["messages"][0]["mine"])

    def test_cannot_request_closed_or_own_dert(self):
        self.dert.open_to_chat = False
        self.dert.save()
        self.client.force_login(self.helper)
        url = reverse("sohbet:request", args=[self.dert.public_id])
        self.client.post(url, {"intro": "Merhaba, ben de benzer bir şey yaşadım."})
        self.client.force_login(self.owner)
        self.client.post(url, {"intro": "Kendi derdime istek göndermeyi deniyorum."})
        self.assertFalse(Conversation.objects.exists())

    def test_duplicate_open_request_blocked(self):
        start_conversation(self.helper, self.owner, self.dert, "Merhaba, dertleşelim mi?")
        with self.assertRaises(ChatError):
            start_conversation(self.helper, self.owner, self.dert, "Tekrar merhaba!")

    def test_blocked_user_cannot_request_or_send(self):
        conv = start_conversation(self.helper, self.owner, self.dert, "Merhaba, dertleşelim mi?")
        conv.status = "active"
        conv.save()
        block_user(self.owner, self.helper)
        conv.refresh_from_db()
        self.assertEqual(conv.status, "closed")
        with self.assertRaises(ChatError):
            start_conversation(self.helper, self.owner, self.dert, "Yeniden deneyeyim")
        self.client.force_login(self.helper)
        self.assertEqual(self.client.get(reverse("sohbet:request", args=[self.dert.public_id])).status_code, 404)

    def test_anonymous_owner_stays_anonymous_in_chat(self):
        self.dert.is_anonymous = True
        self.dert.save()
        conv = start_conversation(self.helper, self.owner, self.dert, "Merhaba, dertleşelim mi?")
        conv.status = "active"
        conv.save()
        self.client.force_login(self.helper)
        for url in (conv.get_absolute_url(), reverse("sohbet:inbox")):
            response = self.client.get(url)
            self.assertContains(response, "Anonim dert ortağı")
            self.assertNotContains(response, "Dert_Sahibi")

    def test_match_request_requires_metoo(self):
        url = reverse("sohbet:match", args=[self.dert.public_id, self.helper.public_id])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 404)
        Reaction.objects.create(dert=self.dert, user=self.helper, kind="metoo")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url, {"intro": "Merhaba, ikimiz de aynı dertteyiz galiba."})
        conv = Conversation.objects.get()
        self.assertEqual((conv.initiator, conv.recipient), (self.owner, self.helper))

    def test_unread_badge(self):
        conv = start_conversation(self.helper, self.owner, self.dert, "Merhaba, dertleşelim mi?")
        self.assertEqual(Conversation.objects.attention_count(self.owner), 1)  # bekleyen istek
        conv.status = "active"
        conv.save()
        conv.mark_read(self.owner)
        send_message(conv, self.helper, "Yeni mesaj")
        self.assertEqual(Conversation.objects.attention_count(self.owner), 1)
        conv.mark_read(self.owner)
        self.assertEqual(Conversation.objects.attention_count(self.owner), 0)
