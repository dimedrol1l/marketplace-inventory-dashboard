from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .integrations.ozon import OzonClient, map_order_lines, map_stock_items
from .models import Order, OzonSync, StockBalance


class OzonMappingTests(TestCase):
    def test_stock_mapping_subtracts_reserved_and_keeps_fulfillment_type(self):
        rows = map_stock_items(
            [
                {
                    "offer_id": "seller-123",
                    "name": "Товар",
                    "stocks": [
                        {"type": "fbo", "present": 12, "reserved": 3},
                        {"type": "fbs", "present": 5, "reserved": 0},
                    ],
                }
            ]
        )

        self.assertEqual(
            rows,
            [
                {
                    "warehouse": "Ozon FBO",
                    "sku": "seller-123",
                    "product_name": "Товар",
                    "available_quantity": 9,
                    "reserved_quantity": 3,
                },
                {
                    "warehouse": "Ozon FBS",
                    "sku": "seller-123",
                    "product_name": "Товар",
                    "available_quantity": 5,
                    "reserved_quantity": 0,
                },
            ],
        )

    def test_order_mapping_preserves_each_product_line(self):
        rows = map_order_lines(
            [
                {
                    "order_id": 42,
                    "posting_number": "123-456-1",
                    "created_at": "2026-10-20T10:00:00Z",
                    "status": "delivering",
                    "products": [
                        {"offer_id": "sku-a", "name": "A", "quantity": 2, "price": "19.90"},
                        {"offer_id": "sku-b", "name": "B", "quantity": 1, "price": "25"},
                    ],
                }
            ]
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual([row["sku"] for row in rows], ["sku-a", "sku-b"])
        self.assertEqual(rows[0]["order_id"], "42")
        self.assertEqual(str(rows[0]["price"]), "19.90")

    def test_client_paginates_v4_order_results_with_cursor(self):
        session = Mock()
        session.post.side_effect = [
            Mock(
                status_code=200,
                json=lambda: {"postings": [{"order_id": 1}, {"order_id": 2}], "has_next": True, "cursor": "page-2"},
            ),
            Mock(status_code=200, json=lambda: {"postings": [{"order_id": 3}], "has_next": False, "cursor": ""}),
        ]
        client = OzonClient("client", "secret", session=session)

        result = client.fetch_orders(page_size=2)

        self.assertEqual([order["order_id"] for order in result], [1, 2, 3])
        self.assertEqual(session.post.call_count, 2)
        self.assertTrue(session.post.call_args_list[0].args[0].endswith("/v4/posting/fbs/list"))
        self.assertEqual(session.post.call_args_list[1].kwargs["json"]["cursor"], "page-2")

    def test_client_paginates_v4_stocks_with_cursor(self):
        session = Mock()
        session.post.side_effect = [
            Mock(
                status_code=200,
                json=lambda: {
                    "result": {
                        "items": [{"offer_id": "sku-1", "stocks": [{"type": "fbs", "present": 5, "reserved": 1}]}],
                        "cursor": "page-2",
                    }
                },
            ),
            Mock(
                status_code=200,
                json=lambda: {
                    "result": {
                        "items": [{"offer_id": "sku-2", "stocks": [{"type": "fbo", "present": 3, "reserved": 0}]}],
                        "cursor": "",
                    }
                },
            ),
        ]
        client = OzonClient("client", "secret", session=session)

        result = client.fetch_stocks()

        self.assertEqual([row["sku"] for row in result], ["sku-1", "sku-2"])
        self.assertEqual(session.post.call_args_list[0].args[0].endswith("/v4/product/info/stocks"), True)
        self.assertEqual(session.post.call_args_list[1].kwargs["json"]["cursor"], "page-2")


class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner", password="test-password")
        self.client.force_login(self.user)

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_dashboard_renders_saved_stock_balances(self):
        StockBalance.objects.create(
            source=StockBalance.Source.OWN,
            warehouse="Основной",
            sku="sku-1",
            product_name="Тестовый товар",
            available_quantity=4,
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тестовый товар")
        self.assertContains(response, "sku-1")

    def test_own_stock_form_updates_same_warehouse_and_sku(self):
        url = reverse("save_own_stock")
        payload = {
            "warehouse": "Основной",
            "sku": "sku-1",
            "product_name": "Тестовый товар",
            "available_quantity": "7",
        }
        self.client.post(url, payload)
        self.client.post(url, {**payload, "available_quantity": "9"})

        self.assertEqual(StockBalance.objects.filter(source="own", warehouse="Основной", sku="sku-1").count(), 1)
        stock = StockBalance.objects.get(source="own", warehouse="Основной", sku="sku-1")
        self.assertEqual(stock.available_quantity, 9)
        self.assertEqual(stock.reserved_quantity, 0)

    @override_settings(OZON_CLIENT_ID="demo-client", OZON_API_KEY="demo-key")
    @patch("cy19346_project.views.OzonClient")
    def test_sync_saves_order_lines_stocks_and_sync_record(self, client_class):
        client_class.return_value.fetch_orders.return_value = [
            {
                "order_id": 45,
                "posting_number": "45-1",
                "created_at": "2026-10-20T10:00:00Z",
                "status": "delivering",
                "products": [
                    {"offer_id": "sku-1", "name": "Товар", "quantity": 1, "price": "20"},
                    {"offer_id": "sku-2", "name": "Другой товар", "quantity": 2, "price": "10"},
                ],
            }
        ]
        client_class.return_value.fetch_stocks.return_value = [
            {
                "warehouse": "Ozon FBO",
                "sku": "sku-1",
                "product_name": "Товар",
                "available_quantity": 8,
                "reserved_quantity": 2,
            }
        ]

        response = self.client.post(reverse("sync_ozon"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(StockBalance.objects.get(source="ozon").available_quantity, 8)
        self.assertEqual(OzonSync.objects.get().imported_orders, 2)

    @override_settings(OZON_CLIENT_ID="", OZON_API_KEY="")
    @patch("cy19346_project.views.OzonClient")
    def test_sync_without_credentials_does_not_call_api(self, client_class):
        self.client.post(reverse("sync_ozon"))
        client_class.assert_not_called()
