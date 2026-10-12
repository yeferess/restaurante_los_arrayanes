from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_dailyordercounter_order_daily_number_order_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="admin_note",
            field=models.CharField(blank=True, max_length=300),
        ),
    ]
