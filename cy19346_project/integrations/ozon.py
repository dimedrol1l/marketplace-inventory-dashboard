from datetime import timedelta, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation

import requests
from django.utils import timezone
from django.utils.dateparse import parse_datetime


class OzonAPIError(Exception):
    """A safe, user-facing error from an Ozon Seller API request."""


class OzonClient:
    base_url = "https://api-seller.ozon.ru"

    def __init__(self, client_id, api_key, *, session=None, timeout=15):
        self.client_id = client_id
        self.api_key = api_key
        self.session = session or requests.Session()
        self.timeout = timeout

    def _post(self, path, payload):
        try:
            response = self.session.post(
                f"{self.base_url}{path}",
                headers={
                    "Client-Id": self.client_id,
                    "Api-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise OzonAPIError("Ozon вернул ответ в неожиданном формате.")
            return payload
        except requests.Timeout as exc:
            raise OzonAPIError("Ozon не ответил вовремя. Попробуйте синхронизацию ещё раз.") from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            if status_code in (401, 403):
                message = "Ozon отклонил доступ. Проверьте Client ID, API-ключ и права ключа."
            else:
                message = f"Ozon вернул ошибку HTTP {status_code}."
            raise OzonAPIError(message) from exc
        except ValueError as exc:
            raise OzonAPIError("Ozon вернул ответ, который не удалось прочитать.") from exc
        except requests.RequestException as exc:
            raise OzonAPIError("Не удалось связаться с Ozon. Проверьте подключение и повторите попытку.") from exc

    def fetch_orders(self, *, days=30, page_size=100):
        now = timezone.now()
        since = now - timedelta(days=days)
        limit = page_size
        cursor = ""
        seen_cursors = set()
        all_orders = []

        while True:
            payload = self._post(
                "/v4/posting/fbs/list",
                {
                    "sort_dir": "asc",
                    "filter": {
                        "since": since.astimezone(datetime_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "to": now.astimezone(datetime_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                    "limit": limit,
                    "cursor": cursor,
                    "with": {
                        "analytics_data": False,
                        "financial_data": False,
                        "barcodes": False,
                    },
                },
            )
            postings = payload.get("postings", [])
            if not isinstance(postings, list):
                raise OzonAPIError("Ozon вернул некорректный список заказов.")
            all_orders.extend(postings)
            if not payload.get("has_next", False):
                return all_orders
            next_cursor = payload.get("cursor", "")
            if not next_cursor or next_cursor in seen_cursors:
                raise OzonAPIError("Ozon вернул некорректный курсор списка заказов.")
            seen_cursors.add(next_cursor)
            cursor = next_cursor

    def fetch_stocks(self, *, page_size=1000):
        cursor = ""
        stocks = []
        seen_cursors = set()

        while True:
            payload = self._post(
                "/v4/product/info/stocks",
                {
                    "filter": {
                        "offer_id": [],
                        "product_id": [],
                        "visibility": "ALL",
                    },
                    "limit": page_size,
                    "cursor": cursor,
                },
            )
            result = payload.get("result", {})
            if not isinstance(result, dict) or not isinstance(result.get("items", []), list):
                raise OzonAPIError("Формат остатков Ozon изменился.")

            items = result.get("items", [])
            stocks.extend(map_stock_items(items))
            next_cursor = result.get("cursor", "")
            if not next_cursor or not items:
                return stocks
            if next_cursor in seen_cursors:
                raise OzonAPIError("Ozon вернул повторяющийся курсор остатков.")
            seen_cursors.add(next_cursor)
            cursor = next_cursor


def map_stock_items(items):
    """Convert Ozon stock records into warehouse-level balance rows."""
    rows = []
    for item in items:
        sku = str(item.get("offer_id") or item.get("product_id") or "").strip()
        if not sku:
            continue
        product_name = item.get("name", "") or ""
        item_stocks = item.get("stocks") or []
        if not isinstance(item_stocks, list):
            raise OzonAPIError("Ozon вернул некорректные остатки товара.")
        for stock in item_stocks:
            stock_type = str(stock.get("type") or "Ozon")
            present = _as_int(stock.get("present", 0))
            reserved = _as_int(stock.get("reserved", 0))
            rows.append(
                {
                    "warehouse": f"Ozon {stock_type.upper()}",
                    "sku": sku,
                    "product_name": product_name,
                    "available_quantity": max(0, present - reserved),
                    "reserved_quantity": max(0, reserved),
                }
            )
    return rows


def map_order_lines(postings):
    """Flatten Ozon postings while retaining one row per product line."""
    rows = []
    for posting in postings:
        order_id = str(posting.get("order_id") or posting.get("posting_number") or "").strip()
        if not order_id:
            continue
        created_at = _parse_datetime(posting.get("created_at"))
        for product in posting.get("products", []):
            sku = str(product.get("offer_id") or product.get("sku") or "").strip()
            if not sku:
                continue
            try:
                price = Decimal(str(product["price"])) if product.get("price") is not None else None
            except (InvalidOperation, ValueError):
                price = None
            rows.append(
                {
                    "order_id": order_id,
                    "posting_number": str(posting.get("posting_number") or ""),
                    "status": str(posting.get("status") or "pending"),
                    "created_at": created_at,
                    "sku": sku,
                    "product_name": str(product.get("name") or ""),
                    "quantity": max(0, _as_int(product.get("quantity", 1))),
                    "price": price,
                }
            )
    return rows


def _parse_datetime(value):
    parsed = parse_datetime(value) if isinstance(value, str) else None
    if parsed is None:
        return timezone.now()
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone=timezone.get_current_timezone())
    return parsed


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
