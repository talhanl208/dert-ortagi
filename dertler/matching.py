"""
Eşleşme mantığı: aynı derdi yaşayanları bir araya getirmek.

Bilerek basit tutuldu: aynı kategori + başlık/özet kelime benzerliği.
Daha gelişmiş eşleşme fikirleri için README'deki yol haritasına bak.
"""

from core.text import similarity, tokens

from .models import Dert

CANDIDATE_POOL = 200


def _dert_tokens(dert):
    return tokens(f"{dert.title} {dert.summary}")


def similar_dertler(dert, viewer, limit=4, only_open=False):
    qs = (
        Dert.objects.visible_to(viewer)
        .filter(category_id=dert.category_id, status=Dert.Status.ACTIVE)
        .exclude(pk=dert.pk)
        .exclude(author_id=dert.author_id)
        .select_related("author", "category")
    )
    if only_open:
        qs = qs.filter(open_to_chat=True)
    if viewer.is_authenticated:
        qs = qs.exclude(author_id=viewer.pk)
    candidates = list(qs.order_by("-created_at")[:CANDIDATE_POOL])
    base = _dert_tokens(dert)
    scored = [(similarity(base, _dert_tokens(c)), c.created_at, c) for c in candidates]
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[2] for row in scored[:limit]]
