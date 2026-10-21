from django.db import migrations

CATEGORIES = [
    ("Aşk ve İlişkiler", "ask-iliskiler", "💞", "rose"),
    ("Aile", "aile", "🏡", "sun"),
    ("Okul ve Sınavlar", "okul-sinavlar", "📚", "sky"),
    ("İş ve Kariyer", "is-kariyer", "💼", "turq"),
    ("Arkadaşlık", "arkadaslik", "🤝", "leaf"),
    ("Yalnızlık", "yalnizlik", "🌙", "lilac"),
    ("Kayıp ve Yas", "kayip-yas", "🕊️", "sky"),
    ("Para ve Geçim", "para-gecim", "🪙", "sun"),
    ("Sağlık", "saglik", "🌿", "leaf"),
    ("Gelecek Kaygısı", "gelecek-kaygisi", "🧭", "turq"),
    ("Kendimle İlgili", "kendimle-ilgili", "🪞", "lilac"),
    ("Diğer", "diger", "✨", "rose"),
]


def seed(apps, schema_editor):
    Category = apps.get_model("dertler", "Category")
    for order, (name, slug, emoji, color) in enumerate(CATEGORIES):
        Category.objects.update_or_create(
            slug=slug, defaults={"name": name, "emoji": emoji, "color": color, "order": order}
        )


def unseed(apps, schema_editor):
    Category = apps.get_model("dertler", "Category")
    Category.objects.filter(slug__in=[c[1] for c in CATEGORIES], dertler__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("dertler", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
