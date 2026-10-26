from django.db import transaction

from .integrations.ozon import map_order_lines
from .models import Order, OzonSync, StockBalance


@transaction.atomic
def save_ozon_data(postings, stock_rows):
    order_lines = map_order_lines(postings)
    for line in order_lines:
        Order.objects.update_or_create(
            marketplace="ozon",
            order_id=line["order_id"],
            sku=line["sku"],
            defaults={key: value for key, value in line.items() if key not in {"order_id", "sku"}},
        )

    StockBalance.objects.filter(source=StockBalance.Source.OZON).delete()
    StockBalance.objects.bulk_create(
        [
            StockBalance(
                source=StockBalance.Source.OZON,
                warehouse=stock["warehouse"],
                sku=stock["sku"],
                product_name=stock["product_name"],
                available_quantity=stock["available_quantity"],
                reserved_quantity=stock["reserved_quantity"],
            )
            for stock in stock_rows
        ]
    )

    sync = OzonSync.objects.create(
        imported_orders=len(order_lines),
        updated_stock_rows=len(stock_rows),
    )
    return sync
