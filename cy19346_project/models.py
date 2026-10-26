from django.db import models
from django.utils import timezone


class Order(models.Model):
    """One imported product line from an Ozon posting."""

    marketplace = models.CharField(max_length=20, default="ozon")
    order_id = models.CharField(max_length=100)
    posting_number = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=60, default="pending")
    created_at = models.DateTimeField(default=timezone.now)
    sku = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "order_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["marketplace", "order_id", "sku"],
                name="unique_marketplace_order_sku",
            )
        ]

    def __str__(self):
        return f"{self.marketplace}: {self.order_id} / {self.sku}"


class StockBalance(models.Model):
    """Latest known stock by source, warehouse and seller SKU."""

    class Source(models.TextChoices):
        OZON = "ozon", "Ozon"
        OWN = "own", "Собственный склад"

    source = models.CharField(max_length=20, choices=Source.choices)
    warehouse = models.CharField(max_length=120)
    sku = models.CharField(max_length=100)
    product_name = models.CharField(max_length=255, blank=True)
    available_quantity = models.IntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source", "warehouse", "sku"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "warehouse", "sku"],
                name="unique_stock_source_warehouse_sku",
            )
        ]

    def __str__(self):
        return f"{self.sku} — {self.warehouse}: {self.available_quantity}"


class OzonSync(models.Model):
    completed_at = models.DateTimeField(auto_now_add=True)
    imported_orders = models.PositiveIntegerField(default=0)
    updated_stock_rows = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"Ozon sync at {self.completed_at:%Y-%m-%d %H:%M}"
