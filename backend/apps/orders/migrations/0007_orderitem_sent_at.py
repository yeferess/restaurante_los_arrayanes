from django.db import migrations, models
from django.db.models import F, OuterRef, Subquery
from django.db.models.functions import Coalesce


def mark_existing_items_as_sent(apps, schema_editor):
    """Every line of an order already out of draft was, until now, sent
    the moment it was added — none may show up as "Sin enviar"."""
    Order = apps.get_model("orders", "Order")
    OrderItem = apps.get_model("orders", "OrderItem")
    order_sent_at = Order.objects.filter(pk=OuterRef("order_id")).values("sent_at")[:1]
    OrderItem.objects.exclude(order__status="DRAFT").update(
        sent_at=Coalesce(Subquery(order_sent_at), F("created_at"))
    )


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_order_admin_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(mark_existing_items_as_sent, migrations.RunPython.noop),
    ]
