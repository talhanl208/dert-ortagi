"""
Sitede dönen güzel sözler.

Yalnızca atasözleri, halk sözleri, telif süresi çoktan dolmuş eserler
(ör. Yunus Emre) ve proje için yazılmış özgün cümleler kullanılır.
Kaynağı belirsiz "ünlü sözler" bilerek eklenmedi.
"""

import datetime
import secrets

QUOTES = [
    ("Derdini söylemeyen derman bulamaz.", "Atasözü"),
    ("Kara gün kararıp kalmaz.", "Atasözü"),
    ("Dost kara günde belli olur.", "Atasözü"),
    ("Bir elin nesi var, iki elin sesi var.", "Atasözü"),
    ("Umut fakirin ekmeğidir.", "Atasözü"),
    ("Damlaya damlaya göl olur.", "Atasözü"),
    ("Bir fincan kahvenin kırk yıl hatırı vardır.", "Atasözü"),
    ("Gönül ne kahve ister ne kahvehane, gönül sohbet ister, kahve bahane.", "Halk sözü"),
    ("Paylaşılan sevinç çoğalır, paylaşılan dert azalır.", "Halk sözü"),
    ("Her gecenin bir sabahı vardır.", "Halk sözü"),
    ("Sevelim sevilelim, dünya kimseye kalmaz.", "Yunus Emre"),
    ("Bugün biraz ağır olabilir. Ama onu tek başına taşımak zorunda değilsin.", "Dert Ortağı"),
    ("Küçük adımlar da adımdır. Bugün attığın adım yeter.", "Dert Ortağı"),
    ("Anlattığın her dert, bir başkasına “yalnız değilmişim” dedirtir.", "Dert Ortağı"),
    ("Bir arkadaşına nasıl davranıyorsan kendine de öyle davran.", "Dert Ortağı"),
    ("Çaylar benden, dertleşmek senden.", "Dert Ortağı"),
    ("Dinlemek de bir iyiliktir. Bazen en büyüğü.", "Dert Ortağı"),
]


def quote_of_the_day(today: datetime.date | None = None):
    today = today or datetime.date.today()
    text, source = QUOTES[today.toordinal() % len(QUOTES)]
    return {"text": text, "source": source}


def random_quote():
    text, source = secrets.choice(QUOTES)
    return {"text": text, "source": source}
