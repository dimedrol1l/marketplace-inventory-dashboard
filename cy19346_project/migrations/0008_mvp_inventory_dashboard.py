from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cy19346_project", "0007_profile"),
    ]

    operations = [
        migrations.RemoveField(model_name="order", name="cancel_reason_id"),
        migrations.RemoveField(model_name="order", name="in_process_at"),
        migrations.RemoveField(model_name="order", name="shipment_date"),
        migrations.RemoveField(model_name="order", name="offer_id"),
        migrations.RemoveField(model_name="order", name="mandatory_mark"),
        migrations.RemoveField(model_name="order", name="barcodes"),
        migrations.RemoveField(model_name="order", name="analytics_data"),
        migrations.RemoveField(model_name="order", name="financial_data"),
        migrations.RemoveField(model_name="order", name="is_fraud"),
        migrations.RemoveField(model_name="order", name="customer_id"),
        migrations.RemoveField(model_name="order", name="order_date"),
        migrations.RemoveField(
            model_name="order",
            name="user",
        ),
        migrations.AlterField(
            model_name="order",
            name="order_id",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="order",
            name="posting_number",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="order",
            name="sku",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="order",
            name="product_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="order",
            name="quantity",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterModelOptions(
            name="order",
            options={"ordering": ["-created_at", "order_id"]},
        ),
        migrations.AlterModelTable(
            name="order",
            table=None,
        ),
        migrations.AddField(
            model_name="order",
            name="marketplace",
            field=models.CharField(default="ozon", max_length=20),
        ),
        migrations.DeleteModel(
            name="APIKey",
        ),
        migrations.DeleteModel(
            name="Profile",
        ),
        migrations.CreateModel(
            name="StockBalance",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("ozon", "Ozon"), ("own", "Собственный склад")],
                        max_length=20,
                    ),
                ),
                ("warehouse", models.CharField(max_length=120)),
                ("sku", models.CharField(max_length=100)),
                ("product_name", models.CharField(blank=True, max_length=255)),
                ("available_quantity", models.IntegerField(default=0)),
                ("reserved_quantity", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["source", "warehouse", "sku"]},
        ),
        migrations.CreateModel(
            name="OzonSync",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
                ("imported_orders", models.PositiveIntegerField(default=0)),
                ("updated_stock_rows", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["-completed_at"]},
        ),
        migrations.AddConstraint(
            model_name="order",
            constraint=models.UniqueConstraint(
                fields=("marketplace", "order_id", "sku"),
                name="unique_marketplace_order_sku",
            ),
        ),
        migrations.AddConstraint(
            model_name="stockbalance",
            constraint=models.UniqueConstraint(
                fields=("source", "warehouse", "sku"),
                name="unique_stock_source_warehouse_sku",
            ),
        ),
    ]
