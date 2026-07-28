#!/usr/bin/env python3
"""Validate the generated cross-border e-commerce mock data package."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

DATA_DIR = Path(__file__).resolve().parent
REPORT_PATH = DATA_DIR / "validation_report.md"

FILES = {
    "products.csv": ("product_id", ["product_id", "title", "site", "currency", "price", "cost", "is_mock_data"]),
    "skus.csv": ("sku_id", ["sku_id", "product_id", "seller_sku", "price", "cost", "is_mock_data"]),
    "inventory.csv": ("inventory_id", ["inventory_id", "sku_id", "available_stock", "stock_status", "is_mock_data"]),
    "reviews.csv": (
        "review_id",
        [
            "review_id", "product_id", "sku_id", "order_id", "buyer_id",
            "rating", "content", "content_zh", "language",
            "sentiment_hint", "issue_type", "is_mock_data",
        ],
    ),
    "orders.csv": ("order_id", ["order_id", "buyer_id", "site", "order_status", "subtotal", "total_amount", "is_mock_data"]),
    "order_items.csv": ("order_item_id", ["order_item_id", "order_id", "product_id", "sku_id", "quantity", "subtotal", "is_mock_data"]),
    "logistics.csv": ("logistics_id", ["logistics_id", "order_id", "tracking_number", "logistics_status", "is_mock_data"]),
    "logistics_tracks.csv": ("track_id", ["track_id", "tracking_number", "status", "event_time", "is_mock_data"]),
    "customer_sessions.csv": ("session_id", ["session_id", "buyer_id", "order_id", "product_id", "intent", "is_mock_data"]),
    "customer_messages.csv": ("message_id", ["message_id", "session_id", "sender_type", "content", "is_mock_data"]),
    "returns_refunds.csv": ("return_id", ["return_id", "order_id", "order_item_id", "buyer_id", "amount", "status", "is_mock_data"]),
    "category_trends.csv": ("trend_id", ["trend_id", "site", "category_id", "date", "search_index", "is_mock_data"]),
}


class Validator:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.failed: list[str] = []
        self.data: dict[str, list[dict[str, str]]] = {}

    def pass_(self, text: str) -> None:
        self.passed.append(text)
        print(f"[PASS] {text}")

    def warn(self, text: str) -> None:
        self.warnings.append(text)
        print(f"[WARN] {text}")

    def fail(self, text: str) -> None:
        self.failed.append(text)
        print(f"[FAIL] {text}")

    def check(self, condition: bool, success: str, failure: str) -> None:
        self.pass_(success) if condition else self.fail(failure)

    def load_files(self) -> None:
        for filename, (_, required) in FILES.items():
            path = DATA_DIR / filename
            if not path.exists():
                self.fail(f"Missing required file: {filename}")
                continue
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.data[filename] = rows
            if not rows:
                self.fail(f"{filename} contains no data rows")
                continue
            missing_cols = sorted(set(required) - set(rows[0]))
            self.check(not missing_cols, f"{filename} contains required columns", f"{filename} missing columns: {missing_cols}")
            self.pass_(f"{filename} loaded: {len(rows)} data rows")

    def primary_keys_and_required(self) -> None:
        for filename, (pk, required) in FILES.items():
            rows = self.data.get(filename, [])
            values = [row.get(pk, "") for row in rows]
            self.check(len(values) == len(set(values)) and all(values), f"{filename} primary key {pk} is unique", f"{filename} has duplicate or empty {pk}")
            empty = [(i + 2, col) for i, row in enumerate(rows) for col in required if row.get(col, "").strip() == ""]
            self.check(not empty, f"{filename} required fields are complete", f"{filename} has {len(empty)} empty required values")
            mock_bad = [row.get(pk, "?") for row in rows if row.get("is_mock_data", "").lower() != "true"]
            self.check(not mock_bad, f"{filename} mock-data flag is complete", f"{filename} has {len(mock_bad)} rows without is_mock_data=true")

    def foreign_keys(self) -> None:
        ids = {name: {r[pk] for r in rows} for name, rows in self.data.items() for pk, _ in [FILES[name]]}
        checks = [
            ("skus.csv", "product_id", "products.csv"),
            ("inventory.csv", "sku_id", "skus.csv"),
            ("reviews.csv", "product_id", "products.csv"),
            ("reviews.csv", "sku_id", "skus.csv"),
            ("reviews.csv", "order_id", "orders.csv"),
            ("order_items.csv", "order_id", "orders.csv"),
            ("order_items.csv", "product_id", "products.csv"),
            ("order_items.csv", "sku_id", "skus.csv"),
            ("logistics.csv", "order_id", "orders.csv"),
            ("logistics_tracks.csv", "tracking_number", "logistics.csv"),
            ("customer_sessions.csv", "order_id", "orders.csv"),
            ("customer_sessions.csv", "product_id", "products.csv"),
            ("customer_messages.csv", "session_id", "customer_sessions.csv"),
            ("returns_refunds.csv", "order_id", "orders.csv"),
            ("returns_refunds.csv", "order_item_id", "order_items.csv"),
        ]
        logistics_tracking = {row["tracking_number"] for row in self.data.get("logistics.csv", [])}
        for child, field, parent in checks:
            parent_ids = logistics_tracking if parent == "logistics.csv" and field == "tracking_number" else ids.get(parent, set())
            missing = [row.get(field, "") for row in self.data.get(child, []) if row.get(field, "") not in parent_ids]
            self.check(not missing, f"{child}.{field} references valid {parent}", f"{child}.{field} has {len(missing)} invalid references")

        sku_product = {r["sku_id"]: r["product_id"] for r in self.data.get("skus.csv", [])}
        mismatch = [r["order_item_id"] for r in self.data.get("order_items.csv", []) if sku_product.get(r["sku_id"]) != r["product_id"]]
        self.check(not mismatch, "Order item SKU-to-product relationships are consistent", f"{len(mismatch)} order items have inconsistent SKU/product")

    def business_rules(self) -> None:
        products = self.data.get("products.csv", [])
        skus = self.data.get("skus.csv", [])
        inventory = self.data.get("inventory.csv", [])
        orders = self.data.get("orders.csv", [])
        items = self.data.get("order_items.csv", [])
        reviews = self.data.get("reviews.csv", [])
        logistics = self.data.get("logistics.csv", [])
        tracks = self.data.get("logistics_tracks.csv", [])
        returns = self.data.get("returns_refunds.csv", [])

        site_currency = {
            "Singapore": "SGD", "Malaysia": "MYR", "Philippines": "PHP",
            "Thailand": "THB", "Vietnam": "VND", "Indonesia": "IDR",
        }
        currency_bad = [r["product_id"] for r in products if site_currency.get(r["site"]) != r["currency"]]
        self.check(not currency_bad, "Product currencies match their sites", f"{len(currency_bad)} products have mismatched site/currency")

        bad_price = [r["product_id"] for r in products if Decimal(r["price"]) < Decimal(r["cost"]) * Decimal("0.95")]
        self.check(not bad_price, "Product prices are reasonable relative to cost", f"{len(bad_price)} products are priced materially below cost")
        bad_sku_price = [r["sku_id"] for r in skus if Decimal(r["price"]) < Decimal(r["cost"])]
        self.check(not bad_sku_price, "SKU prices are not below SKU cost", f"{len(bad_sku_price)} SKUs are priced below cost")

        inv_bad: list[str] = []
        inv_state_bad: list[str] = []
        for r in inventory:
            available, reserved, safety = int(r["available_stock"]), int(r["reserved_stock"]), int(r["safety_stock"])
            if min(available, reserved, safety) < 0:
                inv_bad.append(r["inventory_id"])
            expected = "out_of_stock" if available == 0 else ("low_stock" if available <= safety else "sufficient")
            if r["stock_status"] != expected:
                inv_state_bad.append(r["inventory_id"])
        self.check(not inv_bad, "Inventory quantities are non-negative", f"{len(inv_bad)} inventory rows contain negative quantities")
        self.check(not inv_state_bad, "Inventory status matches available and safety stock", f"{len(inv_state_bad)} inventory status values are inconsistent")

        lines: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        line_math_bad: list[str] = []
        for item in items:
            calc = Decimal(item["unit_price"]) * int(item["quantity"])
            if abs(calc - Decimal(item["subtotal"])) > Decimal("0.01"):
                line_math_bad.append(item["order_item_id"])
            lines[item["order_id"]] += Decimal(item["subtotal"])
        self.check(not line_math_bad, "Order item subtotals are correct", f"{len(line_math_bad)} order item subtotals are incorrect")

        amount_bad: list[str] = []
        state_bad: list[str] = []
        for order in orders:
            subtotal = Decimal(order["subtotal"])
            total = Decimal(order["total_amount"])
            expected = subtotal + Decimal(order["shipping_fee"]) - Decimal(order["discount_amount"])
            if abs(lines[order["order_id"]] - subtotal) > Decimal("0.01") or abs(expected - total) > Decimal("0.01"):
                amount_bad.append(order["order_id"])
            if order["order_status"] == "pending_payment" and (order["paid_at"] or order["shipped_at"]):
                state_bad.append(order["order_id"])
            if order["order_status"] == "cancelled" and order["completed_at"]:
                state_bad.append(order["order_id"])
            if order["order_status"] in {"shipped", "delivered", "completed", "refund_requested", "refunded"} and not order["shipped_at"]:
                state_bad.append(order["order_id"])
        self.check(not amount_bad, "Order amounts reconcile to detail lines, fees, and discounts", f"{len(amount_bad)} order amount relationships are invalid")
        self.check(not state_bad, "Order timestamps and status transitions are coherent", f"{len(state_bad)} orders have status/timestamp conflicts")

        logistics_orders = {r["order_id"] for r in logistics}
        expected_logistics = {r["order_id"] for r in orders if r["order_status"] in {"paid", "ready_to_ship", "shipped", "delivered", "completed", "refund_requested", "refunded"}}
        self.check(expected_logistics <= logistics_orders, "Paid and post-payment orders have logistics records", f"{len(expected_logistics - logistics_orders)} eligible orders lack logistics records")
        pending_conflicts = [r["order_id"] for r in orders if r["order_status"] == "pending_payment" and r["order_id"] in logistics_orders]
        self.check(not pending_conflicts, "Pending-payment orders have not entered logistics", f"{len(pending_conflicts)} pending-payment orders have logistics")

        review_conflicts = []
        for r in reviews:
            rating = int(r["rating"])
            sentiment = r["sentiment_hint"]
            if (rating >= 4 and sentiment == "negative") or (rating <= 2 and sentiment == "positive"):
                review_conflicts.append(r["review_id"])
        self.check(not review_conflicts, "Review ratings align with sentiment hints", f"{len(review_conflicts)} reviews have severe rating/sentiment conflicts")
        self.check(len({r["content"] for r in reviews}) >= 50, "Review text has meaningful multilingual diversity", "Review text diversity is too low")
        unique_translations = {r["content_zh"] for r in reviews}
        self.check(
            len(unique_translations) >= max(100, len(reviews) // 2),
            "Chinese review translations have meaningful per-item diversity",
            f"Chinese review translation diversity is too low: {len(unique_translations)} unique values for {len(reviews)} reviews",
        )
        source_translation_pairs: dict[str, set[str]] = defaultdict(set)
        for review in reviews:
            source_translation_pairs[review["content"]].add(review["content_zh"])
        translation_conflicts = [
            source for source, translations in source_translation_pairs.items()
            if len(translations) > 1
        ]
        self.check(
            not translation_conflicts,
            "Identical source reviews map to one consistent Chinese translation",
            f"{len(translation_conflicts)} source reviews map to conflicting Chinese translations",
        )

        reviews_by_product: dict[str, list[dict[str, str]]] = defaultdict(list)
        for review in reviews:
            reviews_by_product[review["product_id"]].append(review)
        missing_product_reviews = [
            product["product_id"] for product in products
            if product["product_id"] not in reviews_by_product
        ]
        self.check(
            not missing_product_reviews,
            "Every product has linked review evidence",
            f"{len(missing_product_reviews)} products have no reviews",
        )
        one_sided_products = [
            product_id for product_id, product_reviews in reviews_by_product.items()
            if not any(int(review["rating"]) >= 4 for review in product_reviews)
            or not any(int(review["rating"]) <= 2 for review in product_reviews)
        ]
        self.check(
            not one_sided_products,
            "Every product includes both positive and negative review evidence",
            f"{len(one_sided_products)} products have one-sided review sentiment",
        )
        review_count_values = [len(product_reviews) for product_reviews in reviews_by_product.values()]
        self.check(
            len(set(review_count_values)) >= 8 and max(review_count_values) > min(review_count_values) * 2,
            "Per-product review counts follow a non-uniform long-tail distribution",
            "Per-product review counts are too evenly distributed",
        )

        order_map = {r["order_id"]: r for r in orders}
        item_pairs = {(r["order_id"], r["product_id"], r["sku_id"]) for r in items}
        review_link_bad = [
            r["review_id"] for r in reviews
            if order_map[r["order_id"]]["buyer_id"] != r["buyer_id"]
            or (r["order_id"], r["product_id"], r["sku_id"]) not in item_pairs
        ]
        self.check(not review_link_bad, "Reviews match the buyer and item in their linked order", f"{len(review_link_bad)} reviews do not match their linked order")

        ratings: dict[str, list[int]] = defaultdict(list)
        for review in reviews:
            ratings[review["product_id"]].append(int(review["rating"]))
        metric_bad = []
        for product in products:
            values = ratings[product["product_id"]]
            expected_rating = Decimal(str(round(sum(values) / len(values), 2))) if values else Decimal("0")
            if int(product["review_count"]) != len(values) or abs(Decimal(product["rating"]) - expected_rating) > Decimal("0.01"):
                metric_bad.append(product["product_id"])
        self.check(not metric_bad, "Product review counts and average ratings reconcile to reviews", f"{len(metric_bad)} product review metrics do not reconcile")

        grouped: dict[str, list[datetime]] = defaultdict(list)
        for r in tracks:
            grouped[r["tracking_number"]].append(datetime.fromisoformat(r["event_time"]))
        time_bad = [tracking for tracking, times in grouped.items() if times != sorted(times)]
        count_bad = [tracking for tracking, times in grouped.items() if not 2 <= len(times) <= 6]
        self.check(not time_bad, "Logistics track timestamps increase within each tracking number", f"{len(time_bad)} tracking histories are out of order")
        self.check(not count_bad, "Each logistics record has 2–6 track events", f"{len(count_bad)} tracking histories are outside 2–6 events")

        item_map = {r["order_item_id"]: r for r in items}
        return_link_bad = [
            r["return_id"] for r in returns
            if item_map[r["order_item_id"]]["order_id"] != r["order_id"]
            or order_map[r["order_id"]]["buyer_id"] != r["buyer_id"]
        ]
        self.check(not return_link_bad, "Returns match their order item and buyer", f"{len(return_link_bad)} returns do not match their order item or buyer")
        refund_orders = {r["order_id"] for r in orders if r["order_status"] in {"refund_requested", "refunded"}}
        return_orders = {r["order_id"] for r in returns}
        self.check(refund_orders <= return_orders, "Refund-status orders have after-sales records", f"{len(refund_orders - return_orders)} refund-status orders lack after-sales records")

        session_ids = {r["session_id"] for r in self.data.get("customer_sessions.csv", [])}
        msg_counts: dict[str, int] = defaultdict(int)
        for r in self.data.get("customer_messages.csv", []):
            msg_counts[r["session_id"]] += 1
        missing_turns = [sid for sid in session_ids if msg_counts[sid] < 4]
        self.check(not missing_turns, "Customer sessions contain multi-turn conversations", f"{len(missing_turns)} sessions contain fewer than four messages")

        trend_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for r in self.data.get("category_trends.csv", []):
            trend_groups[(r["site"], r["category_id"])].append(r["date"])
        continuity_bad = [key for key, dates in trend_groups.items() if len(dates) != 60 or dates != sorted(dates)]
        self.check(not continuity_bad, "Category trends cover 60 ordered daily observations per site/category", f"{len(continuity_bad)} trend series are incomplete or unordered")

    def report(self) -> None:
        status = "通过" if not self.failed else "失败"
        lines = [
            "# 模拟数据校验报告",
            "",
            f"- 校验状态：**{status}**",
            f"- 通过项：{len(self.passed)}",
            f"- 警告项：{len(self.warnings)}",
            f"- 失败项：{len(self.failed)}",
            "- 数据性质：全部为模拟实验数据，不代表真实 Shopee 生产数据。",
            "",
            "## 文件数量",
            "",
            "| 文件 | 数据行数 |",
            "|---|---:|",
        ]
        for filename in FILES:
            lines.append(f"| {filename} | {len(self.data.get(filename, []))} |")
        for title, values in [("通过项", self.passed), ("警告项", self.warnings), ("失败项", self.failed)]:
            lines.extend(["", f"## {title}", ""])
            lines.extend([f"- {item}" for item in values] or ["- 无"])
        REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nValidation report written to {REPORT_PATH}")


def main() -> int:
    validator = Validator()
    validator.load_files()
    if validator.failed and not validator.data:
        validator.report()
        return 1
    validator.primary_keys_and_required()
    validator.foreign_keys()
    validator.business_rules()
    validator.report()
    return 1 if validator.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
