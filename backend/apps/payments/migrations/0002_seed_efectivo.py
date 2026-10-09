from django.db import migrations


def create_efectivo(apps, schema_editor):
    PaymentAccount = apps.get_model("payments", "PaymentAccount")
    PaymentAccount.objects.get_or_create(
        name="Efectivo", defaults={"is_fixed": True}
    )


def remove_efectivo(apps, schema_editor):
    PaymentAccount = apps.get_model("payments", "PaymentAccount")
    PaymentAccount.objects.filter(name="Efectivo", is_fixed=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_efectivo, remove_efectivo),
    ]
