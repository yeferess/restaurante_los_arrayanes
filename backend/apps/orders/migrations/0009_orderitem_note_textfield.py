from django.db import migrations, models


class Migration(migrations.Migration):
    """RF-4: a merged line (RF-3) keeps one note per line, so the note
    outgrows the old 200-character column."""

    dependencies = [
        ("orders", "0008_order_table_number_nullable"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="note",
            field=models.TextField(blank=True),
        ),
    ]
