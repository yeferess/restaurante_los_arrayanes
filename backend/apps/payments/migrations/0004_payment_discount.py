from django.db import migrations, models


def backfill_subtotal(apps, schema_editor):
    """Charges made before RF-10 had no discount: subtotal == amount."""
    Payment = apps.get_model("payments", "Payment")
    Payment.objects.update(subtotal=models.F("amount"))


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="subtotal",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="payment",
            name="discount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="payment",
            name="discount_reason",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.RunPython(backfill_subtotal, migrations.RunPython.noop),
    ]
