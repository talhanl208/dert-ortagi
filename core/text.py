"""
Metin yardımcıları: Türkçe normalleştirme, kriz ifadesi algılama,
kişisel iletişim bilgisi algılama ve basit benzerlik.

Not: Kriz algılaması kimseyi etiketlemez ve hiçbir yere kaydedilmez.
Yalnızca yazan kişiye o anda destek hatlarını göstermek için kullanılır.
"""

import re

_TR_MAP = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
    }
)


def tr_lower(text: str) -> str:
    """Türkçe kurallarıyla küçük harfe çevirir (I→ı, İ→i)."""
    return (text or "").replace("I", "ı").replace("İ", "i").lower()


def normalize(text: str) -> str:
    """Küçük harf + Türkçe karakterleri ASCII karşılıklarına indirger."""
    lowered = tr_lower(text).translate(_TR_MAP)
    return re.sub(r"\s+", " ", lowered)


# --------------------------------------------------------------------------
# Kriz ifadeleri
# --------------------------------------------------------------------------
_CRISIS_PATTERNS = [
    r"intihar",
    r"kendimi (oldur|oldurmek|oldurece)",
    r"canima kiy",
    r"yasamak istemiyor",
    r"olmek isti",
    r"hayatima son ver",
    r"kendime zarar ver",
    r"kendimi kes",
    r"yasamanin (hicbir |bir )?anlami (yok|kalmadi)",
    r"olsem daha iyi",
    r"her seye son ver",
]
_CRISIS_RE = re.compile("|".join(_CRISIS_PATTERNS))


def looks_like_crisis(*texts: str) -> bool:
    return any(_CRISIS_RE.search(normalize(t)) for t in texts if t)


# --------------------------------------------------------------------------
# İletişim bilgisi (herkese açık dertlerde paylaşılmasın)
# --------------------------------------------------------------------------
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.UNICODE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?90[\s.-]?)?\(?0?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}(?!\d)")
_URL_RE = re.compile(
    r"(https?://|www\.)\S+|\b[\w-]+\.(com|net|org|com\.tr|tr|io|me|ly|gg)\b",
    re.IGNORECASE,
)
_HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9_.]{3,}")


def find_contact_info(text: str) -> list[str]:
    """Metinde bulunan iletişim bilgisi türlerini döner."""
    found = []
    if not text:
        return found
    if _EMAIL_RE.search(text):
        found.append("e-posta adresi")
    if _PHONE_RE.search(text):
        found.append("telefon numarası")
    if _URL_RE.search(text):
        found.append("bağlantı")
    if _HANDLE_RE.search(text):
        found.append("sosyal medya hesabı")
    return found


# --------------------------------------------------------------------------
# Benzerlik (benzer dertleri bulmak için)
# --------------------------------------------------------------------------
# fmt: off
_STOPWORDS = {
    "ve", "ile", "ama", "fakat", "ancak", "bir", "bu", "su", "o", "da", "de", "ki", "mi", "mu",
    "cok", "daha", "en", "gibi", "icin", "ben", "sen", "biz", "siz", "onlar", "beni", "bana",
    "benim", "seni", "sana", "ne", "neden", "nasil", "kadar", "her", "hic", "hep", "artik", "simdi",
    "sonra", "once", "olan", "oldu", "olarak", "var", "yok", "degil", "diye", "ya", "veya", "hem",
    "ise", "kendi", "kendimi", "bile", "bazen", "biraz", "sey", "seyler",
}
# fmt: on


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", normalize(text))
    # Türkçe ekleri kabaca kırpmak için ilk 5 harfi kullan (gövde benzeri).
    return {w[:5] for w in words if len(w) >= 3 and w not in _STOPWORDS}


def similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
