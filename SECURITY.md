# Güvenlik Politikası

Dert Ortağı, insanların en kırılgan anlarını paylaştığı bir yer olarak tasarlandı. Güvenlik açıklarını ciddiye alıyoruz.

## Açık bildirme

Bir güvenlik açığı bulduysan **lütfen herkese açık bir issue açma.** Bunun yerine GitHub'ın gizli bildirim özelliğini kullan:

1. Deponun **Security** sekmesine git.
2. **Report a vulnerability** düğmesine tıkla.
3. Açığı, nasıl yeniden üretileceğini ve olası etkisini anlat.

En kısa sürede dönüş yapılır. Açık düzeltilene kadar ayrıntıları paylaşmaman rica olunur.

## Desteklenen sürümler

Yalnızca `main` dalındaki en güncel sürüm desteklenir.

## Uygulanan önlemler

| Alan | Önlem |
|---|---|
| Gizli bilgiler | Tüm anahtarlar ortam değişkeninden okunur; depoda sır yoktur. `DJANGO_SECRET_KEY` tanımlı değilse uygulama başlamaz. |
| Parolalar | scrypt ile özetlenir, en az 10 karakter, yaygın ve yalnızca rakamdan oluşan parolalar reddedilir. |
| Kaba kuvvet | IP başına giriş/kayıt/parola sıfırlama sınırı, aynı rumuz için 5 hatalı denemede 15 dk kilit, yönetim girişi için ayrı sınır. |
| XSS | Django şablonlarında otomatik kaçış, `|safe` kullanıcı verisinde hiç kullanılmaz, sohbet mesajları istemcide yalnızca `textContent` ile basılır. |
| CSP | `default-src 'self'`, satır içi script/stil yok, üçüncü taraf kaynak yok, `frame-ancestors 'none'`. |
| CSRF | Tüm durum değiştiren işlemler POST + CSRF jetonu; çıkış dahil. |
| Yetkilendirme (IDOR) | Nesneler tahmin edilemeyen UUID ile adreslenir; sohbet ve mesajlara yalnızca taraflar erişebilir, diğerleri 404 alır. |
| Anonimlik | Kullanıcı kimlikleri herkese açık sayfalarda görünmez; anonim derdin sahibi sohbette ve engelleme listesinde de anonim kalır. |
| Taciz önleme | İstek kabul edilmeden mesaj gönderilemez, engelleme iki yönlüdür ve açık sohbetleri kapatır, bekleyen istek sayısı sınırlıdır. |
| Başlıklar | HSTS, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`, COOP, `Permissions-Policy`, oturum açık sayfalarda `Cache-Control: no-store`. |
| Çerezler | `HttpOnly`, `SameSite=Lax`, canlıda `Secure`. |
| Yönetim paneli | `/admin/` yerine ortam değişkeniyle belirlenen adres; özel mesajlar panelde listelenmez. |
| Saldırı yüzeyi | Dosya yükleme yok, istek gövdesi 512 KB ile sınırlı. |
| Bağımlılıklar | Az sayıda bağımlılık; CI'da `pip-audit`, `bandit`, `ruff` (güvenlik kuralları) ve `gitleaks` çalışır, Dependabot açıktır. |

## Bilinen sınırlamalar

- Mesajlar **uçtan uca şifreli değildir**; veritabanında düz metin olarak saklanır.
- Hız sınırlama varsayılan olarak süreç içi bellek önbelleğini kullanır. Birden fazla sunucu süreciyle çalışırken Redis gibi paylaşımlı bir önbellek yapılandırılmalıdır.
- Gerçek zamanlı sohbet yerine birkaç saniyede bir yoklama (polling) kullanılır.
