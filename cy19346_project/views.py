from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import OwnStockForm
from .integrations.ozon import OzonAPIError, OzonClient
from .models import Order, OzonSync, StockBalance
from .services import save_ozon_data


@login_required
def dashboard(request):
    stocks = StockBalance.objects.all()
    recent_orders = Order.objects.filter(created_at__gte=timezone.now() - timedelta(days=30))
    orders_count = recent_orders.count()
    totals = {
        row["source"]: row["total"] or 0
        for row in stocks.values("source").annotate(total=Sum("available_quantity"))
    }
    context = {
        "stocks": stocks,
        "orders": recent_orders[:20],
        "orders_count": orders_count,
        "ozon_stock_total": totals.get(StockBalance.Source.OZON, 0),
        "own_stock_total": totals.get(StockBalance.Source.OWN, 0),
        "last_sync": OzonSync.objects.first(),
        "own_stock_form": OwnStockForm(),
        "ozon_configured": bool(settings.OZON_CLIENT_ID and settings.OZON_API_KEY),
    }
    return render(request, "index.html", context)


@login_required
@require_POST
def sync_ozon(request):
    if not settings.OZON_CLIENT_ID or not settings.OZON_API_KEY:
        messages.error(request, "Добавьте OZON_CLIENT_ID и OZON_API_KEY в локальный файл .env.")
        return redirect("dashboard")

    try:
        client = OzonClient(settings.OZON_CLIENT_ID, settings.OZON_API_KEY)
        postings = client.fetch_orders()
        stock_rows = client.fetch_stocks()
        sync = save_ozon_data(postings, stock_rows)
    except OzonAPIError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(
            request,
            f"Синхронизация завершена: товарных строк заказов — {sync.imported_orders}, "
            f"остатков — {sync.updated_stock_rows}.",
        )
    return redirect("dashboard")


@login_required
@require_POST
def save_own_stock(request):
    form = OwnStockForm(request.POST)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect("dashboard")

    values = form.cleaned_data
    StockBalance.objects.update_or_create(
        source=StockBalance.Source.OWN,
        warehouse=values["warehouse"],
        sku=values["sku"],
        defaults={
            "product_name": values["product_name"],
            "available_quantity": values["available_quantity"],
            "reserved_quantity": 0,
        },
    )
    messages.success(request, "Остаток собственного склада сохранён.")
    return redirect("dashboard")


@login_required
@require_POST
def delete_own_stock(request, pk):
    stock = get_object_or_404(StockBalance, pk=pk, source=StockBalance.Source.OWN)
    stock.delete()
    messages.success(request, "Позиция собственного склада удалена.")
    return redirect("dashboard")
