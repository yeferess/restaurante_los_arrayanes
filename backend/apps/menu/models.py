from django.db import models


class Category(models.Model):
    """Menu category, managed by the admin (RF-1)."""

    name = models.CharField(max_length=50)
    normalized_name = models.CharField(max_length=50, unique=True, editable=False)

    def save(self, *args, **kwargs):
        self.normalized_name = self.name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Menu product, always attached to an existing category (RF-2, RF-3).

    `category` uses PROTECT so the database itself enforces RF-1's rule
    that a category with assigned products can't be deleted.
    """

    name = models.CharField(max_length=100)
    normalized_name = models.CharField(max_length=100, unique=True, editable=False)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.normalized_name = self.name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
