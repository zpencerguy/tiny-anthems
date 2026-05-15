from django.db import migrations


OLD_TO_NEW_BETA_PACKS = {
    "1-credit": (100, 149),
    "2-credits": (190, 279),
    "3-credits": (275, 399),
    "4-credits": (350, 449),
    "5-credits": (400, 499),
}


def update_beta_credit_pack_prices(apps, schema_editor):
    CreditPack = apps.get_model("billing", "CreditPack")
    for slug, (old_price_cents, new_price_cents) in OLD_TO_NEW_BETA_PACKS.items():
        CreditPack.objects.filter(slug=slug, price_cents=old_price_cents).update(
            price_cents=new_price_cents
        )


def restore_old_beta_credit_pack_prices(apps, schema_editor):
    CreditPack = apps.get_model("billing", "CreditPack")
    for slug, (old_price_cents, new_price_cents) in OLD_TO_NEW_BETA_PACKS.items():
        CreditPack.objects.filter(slug=slug, price_cents=new_price_cents).update(
            price_cents=old_price_cents
        )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(update_beta_credit_pack_prices, restore_old_beta_credit_pack_prices),
    ]
