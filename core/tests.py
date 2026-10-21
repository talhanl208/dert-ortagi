from django.test import override_settings
from django.urls import reverse

from core.testing import BaseTestCase, make_user
from core.text import find_contact_info, looks_like_crisis, normalize


class TextTests(BaseTestCase):
    def test_turkish_normalize(self):
        self.assertEqual(normalize("IŞIK İçin ÇĞÜ"), "isik icin cgu")

    def test_crisis_detection_with_and_without_turkish_chars(self):
        self.assertTrue(looks_like_crisis("Artık yaşamak istemiyorum"))
        self.assertTrue(looks_like_crisis("bazen olmek istiyorum"))
        self.assertTrue(looks_like_crisis("KENDİME ZARAR VERDİM"))
        self.assertFalse(looks_like_crisis("Sınav haftası çok yorucu geçiyor"))

    def test_contact_info_detection(self):
        self.assertIn("telefon numarası", find_contact_info("Ara beni 0532 123 45 67"))
        self.assertIn("e-posta adresi", find_contact_info("yaz: ali@example.com"))
        self.assertIn("bağlantı", find_contact_info("www.ornek.com adresine bak"))
        self.assertIn("sosyal medya hesabı", find_contact_info("insta @dertli_kedi"))
        self.assertEqual(find_contact_info("2019 2020 2021 yılları zordu"), [])


class SecurityHeaderTests(BaseTestCase):
    def test_security_headers_present(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("camera=()", response.headers["Permissions-Policy"])

    def test_authenticated_pages_are_not_cached(self):
        user = make_user("Sakin_Baykus")
        self.client.force_login(user)
        response = self.client.get(reverse("sohbet:inbox"))
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_no_third_party_resources_in_pages(self):
        html = self.client.get(reverse("core:home")).content.decode()
        for host in ("googleapis", "gstatic", "cdn.", "unpkg", "jsdelivr", "google-analytics"):
            self.assertNotIn(host, html)

    def test_admin_not_on_default_url(self):
        self.assertEqual(self.client.get("/admin/").status_code, 404)


class PageTests(BaseTestCase):
    def test_legal_pages(self):
        slugs = ("aydinlatma-metni", "acik-riza-metni", "kullanim-kosullari", "topluluk-kurallari", "cerez-politikasi")
        for slug in slugs:
            self.assertEqual(self.client.get(reverse("core:legal", args=[slug])).status_code, 200, slug)
        self.assertEqual(self.client.get("/yasal/olmayan/").status_code, 404)

    def test_support_page_lists_emergency_number(self):
        self.assertContains(self.client.get(reverse("core:support")), "112")


class RateLimitTests(BaseTestCase):
    def test_register_is_rate_limited(self):
        url = reverse("accounts:register")
        for _ in range(5):
            self.client.post(url, {})
        self.assertEqual(self.client.post(url, {}).status_code, 429)


@override_settings(DEBUG=False)
class ErrorPageTests(BaseTestCase):
    def test_friendly_404(self):
        response = self.client.get("/kesinlikle-olmayan-sayfa/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Bu sayfayı bulamadık", status_code=404)
