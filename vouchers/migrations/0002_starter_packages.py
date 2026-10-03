from decimal import Decimal

from django.db import migrations

# Starter packages. The owner can change names and prices in the dashboard.
PACKAGES = [
    ("1 Hour", 60, "1.00"),
    ("3 Hours", 180, "2.50"),
    ("Full Day", 1440, "5.00"),
    ("Weekly", 10080, "20.00"),
]


def add_packages(apps, schema_editor):
    Package = apps.get_model("vouchers", "Package")
    if Package.objects.exists():
        return
    for name, minutes, price in PACKAGES:
        Package.objects.create(name=name, duration_minutes=minutes, price=Decimal(price))


class Migration(migrations.Migration):
    dependencies = [("vouchers", "0001_initial")]
    operations = [migrations.RunPython(add_packages, migrations.RunPython.noop)]
