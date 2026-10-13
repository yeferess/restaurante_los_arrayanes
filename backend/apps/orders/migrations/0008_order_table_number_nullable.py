from django.db import migrations, models


class Migration(migrations.Migration):
    """RF-18: a counter order ("Mostrador") has no table."""

    dependencies = [
        ("orders", "0007_orderitem_sent_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="table_number",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
