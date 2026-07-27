#!/usr/bin/env python3
"""Generate reproducible mock cross-border e-commerce datasets.

All records are synthetic experimental data. No Shopee account, production API,
paid service, web scraping, pandas, or Faker dependency is required.
"""

from __future__ import annotations

import csv
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable

SEED = 20260727
RNG = random.Random(SEED)
OUT_DIR = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
BASE_TIME = datetime(2026, 7, 1, 12, 0, tzinfo=TZ)
MOCK = "true"

SITES = {
    "Singapore": {"currency": "SGD", "language": "English", "city": "Singapore"},
    "Malaysia": {"currency": "MYR", "language": "Malay", "city": "Kuala Lumpur"},
    "Philippines": {"currency": "PHP", "language": "Filipino", "city": "Manila"},
    "Thailand": {"currency": "THB", "language": "Thai", "city": "Bangkok"},
    "Vietnam": {"currency": "VND", "language": "Vietnamese", "city": "Ho Chi Minh City"},
    "Indonesia": {"currency": "IDR", "language": "Indonesian", "city": "Jakarta"},
}

CATEGORIES = [
    ("CAT001", "Consumer Electronics"),
    ("CAT002", "Home & Living"),
    ("CAT003", "Beauty & Personal Care"),
    ("CAT004", "Fashion Accessories"),
    ("CAT005", "Sports & Outdoors"),
    ("CAT006", "Pet Supplies"),
    ("CAT007", "Kitchen Appliances"),
    ("CAT008", "Baby Products"),
]

CATEGORY_PRODUCTS = {
    "Consumer Electronics": [
        ("Wireless Earbuds", "Bluetooth 5.3, low-latency audio and charging case", "Color", ["Black", "White", "Blue"]),
        ("Portable Charger", "Fast-charging power bank with safety protection", "Capacity", ["10000mAh", "20000mAh"]),
        ("USB-C Hub", "Multi-port hub for laptop and tablet workflows", "Ports", ["6-in-1", "8-in-1"]),
        ("Smart Desk Lamp", "Adjustable LED lamp with touch controls", "Color", ["White", "Grey"]),
    ],
    "Home & Living": [
        ("Storage Organizer", "Foldable household organizer for compact spaces", "Size", ["Small", "Medium", "Large"]),
        ("Microfiber Towel Set", "Soft quick-dry towels for home and travel", "Color", ["Beige", "Blue", "Pink"]),
        ("Aroma Diffuser", "Quiet mist diffuser with ambient light", "Capacity", ["200ml", "400ml"]),
        ("Vacuum Storage Bags", "Reusable space-saving storage bags", "Pack", ["5 Pack", "10 Pack"]),
    ],
    "Beauty & Personal Care": [
        ("Facial Cleansing Brush", "Gentle silicone cleansing brush for daily skincare", "Color", ["Pink", "Green", "White"]),
        ("Hair Styling Brush", "Heated styling brush with adjustable temperature", "Plug", ["EU", "UK"]),
        ("Makeup Organizer", "Clear cosmetic organizer with modular compartments", "Size", ["Compact", "Large"]),
        ("Travel Bottle Set", "Leak-resistant refillable travel containers", "Color", ["Clear", "Pastel"]),
    ],
    "Fashion Accessories": [
        ("Crossbody Bag", "Lightweight everyday bag with secure compartments", "Color", ["Black", "Khaki", "Green"]),
        ("Polarized Sunglasses", "UV400 polarized lenses in a lightweight frame", "Style", ["Classic", "Sport"]),
        ("Minimalist Watch", "Clean dial design with adjustable strap", "Color", ["Black", "Silver", "Rose Gold"]),
        ("Travel Wallet", "RFID-blocking organizer for cards and passport", "Color", ["Navy", "Brown"]),
    ],
    "Sports & Outdoors": [
        ("Resistance Band Set", "Multi-level bands for home strength training", "Level", ["Light", "Medium", "Heavy"]),
        ("Insulated Water Bottle", "Double-wall bottle for hot and cold drinks", "Capacity", ["500ml", "750ml"]),
        ("Yoga Mat", "Non-slip exercise mat with carrying strap", "Thickness", ["6mm", "8mm"]),
        ("Running Waist Belt", "Sweat-resistant belt for phone and essentials", "Size", ["S-M", "L-XL"]),
    ],
    "Pet Supplies": [
        ("Interactive Cat Toy", "Rechargeable motion toy for indoor cats", "Color", ["Blue", "Orange"]),
        ("Pet Grooming Brush", "Rounded-tip deshedding brush for cats and dogs", "Size", ["Small", "Large"]),
        ("Slow Feeder Bowl", "Maze bowl designed to support slower eating", "Size", ["Small", "Medium"]),
        ("Portable Pet Bottle", "Leak-resistant water bottle for outdoor walks", "Capacity", ["300ml", "500ml"]),
    ],
    "Kitchen Appliances": [
        ("Mini Food Chopper", "Compact chopper for garlic, herbs and vegetables", "Capacity", ["250ml", "500ml"]),
        ("Digital Kitchen Scale", "Precise scale with tare function and clear display", "Color", ["Silver", "Black"]),
        ("Electric Milk Frother", "Handheld frother for coffee and beverages", "Color", ["Black", "White"]),
        ("Sandwich Maker", "Compact non-stick press for quick breakfasts", "Plug", ["EU", "UK"]),
    ],
    "Baby Products": [
        ("Silicone Feeding Set", "Food-grade feeding set with suction base", "Color", ["Blue", "Pink", "Beige"]),
        ("Baby Safety Corner Guards", "Soft transparent guards for furniture corners", "Pack", ["8 Pack", "16 Pack"]),
        ("Portable Changing Mat", "Foldable wipe-clean mat with storage pockets", "Color", ["Grey", "Green"]),
        ("Stroller Organizer", "Universal organizer with insulated cup holders", "Color", ["Black", "Grey"]),
    ],
}

# Base prices are expressed in local currency ranges per market.
PRICE_RANGES = {
    "SGD": (9, 95),
    "MYR": (25, 280),
    "PHP": (250, 3800),
    "THB": (180, 2600),
    "VND": (120000, 1600000),
    "IDR": (80000, 950000),
}

POSITIVE = {
    "English": [
        "Works smoothly and feels sturdier than expected.",
        "Good value, neat packaging, and the color matches the photos.",
        "Easy to use every day; delivery was also quicker than expected.",
        "The finish is clean and the size is exactly right for me.",
        "Very practical design. I would recommend it to friends.",
    ],
    "Malay": [
        "Produk berfungsi dengan baik dan kualitinya memuaskan.",
        "Pembungkusan kemas, warna sama seperti gambar dan mudah digunakan.",
        "Berbaloi dengan harga, penghantaran juga lebih cepat daripada jangkaan.",
        "Saiz sesuai dan bahan terasa kukuh untuk kegunaan harian.",
        "Reka bentuk praktikal dan saya berpuas hati dengan pembelian ini.",
    ],
    "Indonesian": [
        "Produknya berfungsi baik dan kualitasnya lebih bagus dari perkiraan.",
        "Kemasan rapi, warna sesuai foto, dan mudah digunakan.",
        "Harganya sepadan, pengiriman juga cukup cepat.",
        "Ukuran pas dan bahannya terasa kuat untuk dipakai sehari-hari.",
        "Desain praktis, saya puas dengan pembelian ini.",
    ],
    "Thai": [
        "สินค้าใช้งานได้ดีและคุณภาพดีกว่าที่คาดไว้",
        "แพ็กเรียบร้อย สีตรงกับรูป และใช้งานง่าย",
        "คุ้มค่ากับราคา การจัดส่งเร็วกว่าที่คิด",
        "ขนาดพอดีและวัสดุดูแข็งแรงสำหรับใช้ทุกวัน",
        "ดีไซน์ใช้งานได้จริง โดยรวมพอใจกับสินค้านี้",
    ],
    "Vietnamese": [
        "Sản phẩm hoạt động tốt và chất lượng tốt hơn mong đợi.",
        "Đóng gói gọn gàng, màu giống hình và dễ sử dụng.",
        "Đáng tiền, giao hàng cũng nhanh hơn dự kiến.",
        "Kích thước phù hợp và chất liệu khá chắc chắn.",
        "Thiết kế thực tế, tôi hài lòng với sản phẩm này.",
    ],
    "Filipino": [
        "Maayos gamitin at mas matibay kaysa sa inaasahan ko.",
        "Malinis ang packaging, tugma ang kulay sa larawan, at madaling gamitin.",
        "Sulit sa presyo at mas mabilis dumating kaysa sa inaasahan.",
        "Tamang-tama ang sukat at mukhang matibay ang materyal.",
        "Praktikal ang disenyo at nasiyahan ako sa produktong ito.",
    ],
}

NEUTRAL = {
    "English": ["It works as described, though the finish is fairly basic.", "Acceptable for the price; delivery took the usual time."],
    "Malay": ["Produk berfungsi seperti diterangkan, tetapi kemasannya biasa sahaja.", "Sesuai dengan harga; masa penghantaran adalah sederhana."],
    "Indonesian": ["Produk berfungsi sesuai deskripsi, tetapi finishing-nya biasa saja.", "Cukup sesuai harga; waktu pengiriman standar."],
    "Thai": ["สินค้าใช้งานได้ตามรายละเอียด แต่งานประกอบค่อนข้างธรรมดา", "คุณภาพเหมาะกับราคา ระยะเวลาจัดส่งปกติ"],
    "Vietnamese": ["Sản phẩm đúng mô tả nhưng phần hoàn thiện khá cơ bản.", "Chất lượng phù hợp với giá, thời gian giao hàng bình thường."],
    "Filipino": ["Gumagana ayon sa description pero simple lang ang finish.", "Katanggap-tanggap sa presyo at normal ang tagal ng delivery."],
}

NEGATIVE = {
    "product_quality": {
        "English": "The item worked at first, but the build quality feels weak.",
        "Malay": "Produk boleh digunakan pada awalnya, tetapi kualiti binaan terasa lemah.",
        "Indonesian": "Barang sempat berfungsi, tetapi kualitas rakitannya terasa kurang kuat.",
        "Thai": "สินค้าใช้งานได้ช่วงแรก แต่คุณภาพงานประกอบไม่แข็งแรง",
        "Vietnamese": "Sản phẩm dùng được lúc đầu nhưng chất lượng hoàn thiện chưa chắc chắn.",
        "Filipino": "Gumana noong una pero mahina ang kalidad ng pagkakagawa.",
    },
    "packaging": {
        "English": "The product is usable, but the outer box arrived crushed.",
        "Malay": "Produk masih boleh digunakan, tetapi kotak luar tiba dalam keadaan kemek.",
        "Indonesian": "Produknya masih bisa dipakai, tetapi kotak luarnya penyok.",
        "Thai": "สินค้ายังใช้ได้ แต่กล่องด้านนอกมาถึงในสภาพบุบ",
        "Vietnamese": "Sản phẩm vẫn dùng được nhưng hộp bên ngoài bị móp.",
        "Filipino": "Nagagamit pa ang produkto pero yupi ang kahon pagdating.",
    },
    "logistics": {
        "English": "The item was acceptable, but delivery was much later than promised.",
        "Malay": "Produk boleh diterima, tetapi penghantaran jauh lebih lewat daripada jangkaan.",
        "Indonesian": "Barang cukup baik, tetapi pengiriman jauh lebih lambat dari perkiraan.",
        "Thai": "สินค้าใช้ได้ แต่การจัดส่งช้ากว่าที่แจ้งมาก",
        "Vietnamese": "Sản phẩm ổn nhưng giao hàng chậm hơn dự kiến khá nhiều.",
        "Filipino": "Maayos ang item pero masyadong huli ang delivery.",
    },
    "wrong_item": {
        "English": "I received a different variation from the one selected.",
        "Malay": "Saya menerima variasi yang berbeza daripada pilihan saya.",
        "Indonesian": "Saya menerima variasi yang berbeda dari pilihan pesanan.",
        "Thai": "ได้รับตัวเลือกสินค้าไม่ตรงกับที่สั่ง",
        "Vietnamese": "Tôi nhận được phiên bản khác với lựa chọn đã đặt.",
        "Filipino": "Ibang variation ang natanggap ko kaysa sa inorder.",
    },
    "size": {
        "English": "The sizing runs smaller than the measurements shown.",
        "Malay": "Saiz sebenar lebih kecil daripada ukuran yang dinyatakan.",
        "Indonesian": "Ukurannya lebih kecil dibandingkan tabel yang ditampilkan.",
        "Thai": "ขนาดจริงเล็กกว่าตารางวัดที่แสดงไว้",
        "Vietnamese": "Kích thước thực tế nhỏ hơn bảng thông số.",
        "Filipino": "Mas maliit ang actual size kaysa sa nakasaad na sukat.",
    },
    "battery": {
        "English": "Battery life is noticeably shorter than expected.",
        "Malay": "Jangka hayat bateri lebih pendek daripada jangkaan.",
        "Indonesian": "Daya tahan baterai lebih singkat dari yang diharapkan.",
        "Thai": "อายุการใช้งานแบตเตอรี่สั้นกว่าที่คาดไว้",
        "Vietnamese": "Thời lượng pin ngắn hơn đáng kể so với mong đợi.",
        "Filipino": "Mas maikli ang battery life kaysa sa inaasahan.",
    },
    "material": {
        "English": "The material feels thinner than it appears in the listing.",
        "Malay": "Bahan terasa lebih nipis daripada yang kelihatan dalam senarai.",
        "Indonesian": "Bahannya terasa lebih tipis daripada yang terlihat di halaman produk.",
        "Thai": "วัสดุบางกว่าที่เห็นในหน้ารายการสินค้า",
        "Vietnamese": "Chất liệu mỏng hơn so với hình ảnh trên trang sản phẩm.",
        "Filipino": "Mas manipis ang materyal kaysa sa itsura sa listing.",
    },
    "customer_service": {
        "English": "The issue was simple, but it took too long to get a clear reply.",
        "Malay": "Masalahnya mudah, tetapi terlalu lama untuk menerima jawapan yang jelas.",
        "Indonesian": "Masalahnya sederhana, tetapi balasan yang jelas datang terlalu lama.",
        "Thai": "ปัญหาไม่ซับซ้อน แต่ใช้เวลานานกว่าจะได้รับคำตอบที่ชัดเจน",
        "Vietnamese": "Vấn đề đơn giản nhưng mất quá lâu mới nhận được phản hồi rõ ràng.",
        "Filipino": "Simple lang ang problema pero matagal bago nakakuha ng malinaw na sagot.",
    },
}

ZH = {
    "positive": ["使用顺畅，做工比预期更结实。", "包装整洁，颜色与图片一致，性价比不错。", "日常使用很方便，配送也较快。"],
    "neutral": ["功能符合描述，但做工比较普通。", "与价格基本相符，配送速度一般。"],
    "negative": ["商品存在质量或使用体验问题。", "收到的商品或配送服务未达到预期。", "问题处理速度较慢，希望改进。"],
}


def iso(value: datetime | None) -> str:
    """Return ISO 8601 with timezone; empty string for missing timestamps."""
    return value.isoformat(timespec="seconds") if value else ""


def money(value: float | Decimal) -> str:
    """Round monetary values to two decimals using decimal half-up."""
    return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def write_csv(name: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write a list of dictionaries as an Excel-friendly UTF-8-SIG CSV."""
    path = OUT_DIR / name
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def choose_weighted(options: list[tuple[Any, int]]) -> Any:
    values, weights = zip(*options)
    return RNG.choices(values, weights=weights, k=1)[0]


def random_price(currency: str) -> float:
    low, high = PRICE_RANGES[currency]
    raw = RNG.uniform(low, high)
    if currency in {"VND", "IDR"}:
        return float(round(raw / 1000) * 1000)
    if currency in {"PHP", "THB"}:
        return float(round(raw))
    return round(raw, 2)


def generate_products_and_skus() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    products: list[dict[str, Any]] = []
    skus: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    shop_by_site: dict[str, tuple[str, str]] = {}
    for index, site in enumerate(SITES, 1):
        shop_by_site[site] = (f"SHOP{index:03d}", f"Demo {site} Smart Store")

    for idx in range(1, 101):
        category_id, category = CATEGORIES[(idx - 1) % len(CATEGORIES)]
        site = list(SITES)[(idx - 1) % len(SITES)]
        currency = SITES[site]["currency"]
        shop_id, shop_name = shop_by_site[site]
        product_name, description, variation_name, variations = RNG.choice(CATEGORY_PRODUCTS[category])
        title = f"{product_name} {RNG.choice(['Essential', 'Plus', 'Everyday', 'Compact', 'Premium'])} {idx:03d}"
        base_price = random_price(currency)
        cost_ratio = RNG.uniform(0.45, 0.72)
        cost = base_price * cost_ratio
        shipping = base_price * RNG.uniform(0.03, 0.12)
        created = BASE_TIME - timedelta(days=RNG.randint(60, 540), hours=RNG.randint(0, 23))
        updated = BASE_TIME - timedelta(days=RNG.randint(0, 20), hours=RNG.randint(0, 23))
        status = choose_weighted([("active", 82), ("draft", 8), ("inactive", 7), ("archived", 3)])
        products.append(
            {
                "product_id": f"PROD{idx:04d}",
                "shop_id": shop_id,
                "shop_name": shop_name,
                "title": title,
                "category_id": category_id,
                "category_name": category,
                "description": description,
                "platform": "MockShopee",
                "site": site,
                "source_type": "simulated_experiment",
                "currency": currency,
                "price": money(base_price),
                "cost": money(cost),
                "shipping_cost": money(shipping),
                "sales_count": 0,
                "rating": "0.00",
                "review_count": 0,
                "favorite_count": 0,
                "status": status,
                "created_at": iso(created),
                "updated_at": iso(updated),
                "collected_at": iso(BASE_TIME),
                "is_mock_data": MOCK,
            }
        )
        sku_count = RNG.randint(1, 4)
        chosen_variations = RNG.sample(variations, k=min(sku_count, len(variations)))
        while len(chosen_variations) < sku_count:
            chosen_variations.append(f"Style {len(chosen_variations) + 1}")
        for local_idx, variation in enumerate(chosen_variations, 1):
            sku_seq = len(skus) + 1
            sku_id = f"SKU{sku_seq:05d}"
            sku_price = base_price * RNG.uniform(0.92, 1.16)
            sku_cost = min(sku_price * 0.82, cost * RNG.uniform(0.96, 1.08))
            sku_status = "active" if status == "active" else choose_weighted([("active", 2), ("inactive", 8)])
            skus.append(
                {
                    "sku_id": sku_id,
                    "product_id": f"PROD{idx:04d}",
                    "seller_sku": f"{category_id}-{idx:04d}-{local_idx:02d}",
                    "variation_name": variation_name,
                    "variation_value": variation,
                    "price": money(sku_price),
                    "cost": money(sku_cost),
                    "weight": f"{RNG.uniform(0.08, 2.5):.3f}",
                    "status": sku_status,
                    "created_at": iso(created + timedelta(minutes=local_idx)),
                    "is_mock_data": MOCK,
                }
            )
            stock_kind = choose_weighted([("sufficient", 76), ("low_stock", 18), ("out_of_stock", 6)])
            if stock_kind == "sufficient":
                available = RNG.randint(18, 160)
                safety = RNG.randint(5, 15)
            elif stock_kind == "low_stock":
                safety = RNG.randint(5, 15)
                available = RNG.randint(1, safety)
            else:
                available = 0
                safety = RNG.randint(5, 12)
            inventory.append(
                {
                    "inventory_id": f"INV{sku_seq:05d}",
                    "sku_id": sku_id,
                    "warehouse_id": f"WH{(idx % 6) + 1:03d}",
                    "warehouse_name": f"{site} Demo Fulfillment Center",
                    "available_stock": available,
                    "reserved_stock": RNG.randint(0, min(8, max(0, available))),
                    "safety_stock": safety,
                    "stock_status": stock_kind,
                    "updated_at": iso(BASE_TIME - timedelta(hours=RNG.randint(0, 72))),
                    "is_mock_data": MOCK,
                }
            )
    return products, skus, inventory


def generate_orders(
    products: list[dict[str, Any]], skus: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    product_map = {row["product_id"]: row for row in products}
    skus_by_site: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sku in skus:
        site = product_map[sku["product_id"]]["site"]
        skus_by_site[site].append(sku)

    orders: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    statuses = [
        ("pending_payment", 6),
        ("paid", 7),
        ("ready_to_ship", 8),
        ("shipped", 15),
        ("delivered", 14),
        ("completed", 35),
        ("cancelled", 6),
        ("refund_requested", 4),
        ("refunded", 5),
    ]
    for index in range(1, 501):
        order_id = f"ORD{index:06d}"
        site = RNG.choice(list(SITES))
        currency = SITES[site]["currency"]
        created = BASE_TIME - timedelta(days=RNG.randint(2, 180), minutes=RNG.randint(0, 1439))
        status = choose_weighted(statuses)
        item_count = RNG.randint(1, 4)
        selected = RNG.sample(skus_by_site[site], k=item_count)
        subtotal_value = Decimal("0.00")
        for sku in selected:
            quantity = choose_weighted([(1, 74), (2, 20), (3, 6)])
            unit_price = Decimal(sku["price"])
            line_subtotal = unit_price * quantity
            subtotal_value += line_subtotal
            items.append(
                {
                    "order_item_id": f"OI{len(items) + 1:07d}",
                    "order_id": order_id,
                    "product_id": sku["product_id"],
                    "sku_id": sku["sku_id"],
                    "quantity": quantity,
                    "unit_price": money(unit_price),
                    "subtotal": money(line_subtotal),
                    "is_mock_data": MOCK,
                }
            )
        shipping_fee = Decimal(str(round(float(subtotal_value) * RNG.uniform(0.02, 0.08), 2)))
        discount = Decimal(str(round(float(subtotal_value) * choose_weighted([(0, 55), (0.05, 25), (0.1, 15), (0.15, 5)]), 2)))
        total = subtotal_value + shipping_fee - discount
        paid_at = shipped_at = completed_at = cancelled_at = None
        payment_status = "unpaid"
        if status not in {"pending_payment", "cancelled"}:
            paid_at = created + timedelta(hours=RNG.randint(1, 24))
            payment_status = "paid"
        if status in {"shipped", "delivered", "completed", "refund_requested", "refunded"}:
            shipped_at = (paid_at or created) + timedelta(hours=RNG.randint(8, 48))
        if status in {"delivered", "completed", "refund_requested", "refunded"}:
            completed_at = (shipped_at or created) + timedelta(days=RNG.randint(2, 8))
        if status == "cancelled":
            cancelled_at = created + timedelta(hours=RNG.randint(1, 36))
            payment_status = choose_weighted([("unpaid", 75), ("refunded", 25)])
        elif status == "refunded":
            payment_status = "refunded"
        orders.append(
            {
                "order_id": order_id,
                "shop_id": product_map[selected[0]["product_id"]]["shop_id"],
                "buyer_id": f"BUY{RNG.randint(1, 320):05d}",
                "site": site,
                "currency": currency,
                "order_status": status,
                "payment_status": payment_status,
                "subtotal": money(subtotal_value),
                "shipping_fee": money(shipping_fee),
                "discount_amount": money(discount),
                "total_amount": money(total),
                "created_at": iso(created),
                "paid_at": iso(paid_at),
                "shipped_at": iso(shipped_at),
                "completed_at": iso(completed_at),
                "cancelled_at": iso(cancelled_at),
                "is_mock_data": MOCK,
            }
        )
    return orders, items


def generate_reviews(
    products: list[dict[str, Any]],
    skus: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    order_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    product_map = {row["product_id"]: row for row in products}
    order_map = {row["order_id"]: row for row in orders}
    eligible = [
        item
        for item in order_items
        if order_map[item["order_id"]]["order_status"] in {"delivered", "completed", "refund_requested", "refunded"}
    ]
    reviews: list[dict[str, Any]] = []
    issues = list(NEGATIVE)
    for index in range(1, 1001):
        item = RNG.choice(eligible)
        order = order_map[item["order_id"]]
        product = product_map[item["product_id"]]
        language = SITES[product["site"]]["language"]
        rating = choose_weighted([(5, 55), (4, 24), (3, 10), (2, 7), (1, 4)])
        if rating >= 4:
            sentiment = "positive"
            issue = "none"
            content = RNG.choice(POSITIVE[language])
        elif rating == 3:
            sentiment = "neutral"
            issue = choose_weighted([("none", 65), ("packaging", 15), ("logistics", 20)])
            content = RNG.choice(NEUTRAL[language])
        else:
            sentiment = "negative"
            issue = RNG.choice(issues)
            content = NEGATIVE[issue][language]
        # Add light, meaningful variation without turning text into opaque noise.
        suffix = RNG.choice(["", " Overall experience noted.", " This was after several days of use.", " I hope the next batch improves."])
        if language == "English":
            content += suffix
        created = datetime.fromisoformat(order["completed_at"]) + timedelta(days=RNG.randint(0, 21), hours=RNG.randint(0, 23))
        reviews.append(
            {
                "review_id": f"REV{index:06d}",
                "product_id": item["product_id"],
                "sku_id": item["sku_id"],
                "order_id": item["order_id"],
                "buyer_id": order["buyer_id"],
                "rating": rating,
                "content": content,
                "content_zh": RNG.choice(ZH[sentiment]),
                "language": language,
                "sentiment_hint": sentiment,
                "issue_type": issue,
                "created_at": iso(created),
                "is_mock_data": MOCK,
            }
        )
    return reviews


def generate_logistics(orders: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    logistics: list[dict[str, Any]] = []
    tracks: list[dict[str, Any]] = []
    eligible_statuses = {"paid", "ready_to_ship", "shipped", "delivered", "completed", "refund_requested", "refunded"}
    carriers = ["DemoExpress", "MockParcel", "SampleLogistics", "LabShip"]
    for order in orders:
        if order["order_status"] not in eligible_statuses:
            continue
        order_id = order["order_id"]
        tracking = f"TRK{int(order_id[3:]):09d}"
        origin = "Shenzhen Demo Warehouse"
        destination = SITES[order["site"]]["city"]
        status_map = {
            "paid": "pending_pickup",
            "ready_to_ship": "pending_pickup",
            "shipped": choose_weighted([("picked_up", 20), ("in_transit", 55), ("customs_clearance", 15), ("exception", 10)]),
            "delivered": "delivered",
            "completed": "delivered",
            "refund_requested": "delivered",
            "refunded": "delivered",
        }
        logistics_status = status_map[order["order_status"]]
        start = datetime.fromisoformat(order["paid_at"]) if order["paid_at"] else datetime.fromisoformat(order["created_at"])
        possible = [
            ("pending_pickup", "Shenzhen Demo Warehouse", "Shipment information received"),
            ("picked_up", "Shenzhen Sorting Center", "Parcel picked up by carrier"),
            ("in_transit", "Regional Transit Hub", "Parcel is moving to destination"),
            ("customs_clearance", f"{destination} Customs", "Customs processing completed"),
            ("out_for_delivery", f"{destination} Delivery Hub", "Courier is delivering the parcel"),
            ("delivered", destination, "Parcel delivered to the simulated buyer"),
        ]
        final_index = {"pending_pickup": 0, "picked_up": 1, "in_transit": 2, "customs_clearance": 3, "out_for_delivery": 4, "delivered": 5, "exception": 2}[logistics_status]
        if logistics_status == "exception":
            selected_events = possible[:3] + [("exception", "Regional Transit Hub", "Temporary routing exception; manual review required")]
        elif logistics_status == "pending_pickup":
            selected_events = [
                ("pending_pickup", "Shenzhen Demo Warehouse", "Shipment label created"),
                ("pending_pickup", "Shenzhen Demo Warehouse", "Parcel packed and awaiting carrier pickup"),
            ]
        else:
            count = min(RNG.randint(2, 6), final_index + 1)
            event_indices = sorted(set([0, final_index] + RNG.sample(range(final_index + 1), k=min(count, final_index + 1))))
            selected_events = [possible[i] for i in event_indices][:6]
        event_time = start
        for event_status, location, description in selected_events:
            event_time += timedelta(hours=RNG.randint(5, 28))
            tracks.append(
                {
                    "track_id": f"TRACK{len(tracks) + 1:07d}",
                    "tracking_number": tracking,
                    "status": event_status,
                    "location": location,
                    "description": description,
                    "event_time": iso(event_time),
                    "is_mock_data": MOCK,
                }
            )
        latest = selected_events[-1][1]
        logistics.append(
            {
                "logistics_id": f"LOG{len(logistics) + 1:06d}",
                "order_id": order_id,
                "tracking_number": tracking,
                "carrier": RNG.choice(carriers),
                "logistics_status": logistics_status,
                "origin": origin,
                "destination": destination,
                "estimated_delivery_at": iso(start + timedelta(days=RNG.randint(4, 9))),
                "latest_location": latest,
                "updated_at": iso(event_time),
                "is_mock_data": MOCK,
            }
        )
    return logistics, tracks


def generate_returns(
    orders: list[dict[str, Any]], order_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    order_map = {row["order_id"]: row for row in orders}
    by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in order_items:
        by_order[item["order_id"]].append(item)
    preferred = [o for o in orders if o["order_status"] in {"refund_requested", "refunded"}]
    fallback = [o for o in orders if o["order_status"] in {"delivered", "completed"}]
    selected_orders = preferred[:]
    while len(selected_orders) < 50:
        candidate = RNG.choice(fallback)
        if candidate not in selected_orders:
            selected_orders.append(candidate)
    rows: list[dict[str, Any]] = []
    reasons = ["damaged", "wrong_item", "not_as_described", "size_issue", "quality_issue", "late_delivery", "changed_mind"]
    for idx, order in enumerate(selected_orders[:50], 1):
        item = RNG.choice(by_order[order["order_id"]])
        request_type = choose_weighted([("refund_only", 35), ("return_and_refund", 65)])
        reason = RNG.choice(reasons)
        status = "requested" if order["order_status"] == "refund_requested" else choose_weighted([("approved", 30), ("completed", 60), ("rejected", 10)])
        requested = (datetime.fromisoformat(order["completed_at"]) if order["completed_at"] else datetime.fromisoformat(order["created_at"])) + timedelta(days=RNG.randint(1, 14))
        completed = requested + timedelta(days=RNG.randint(1, 7)) if status == "completed" else None
        amount = Decimal(item["subtotal"]) if request_type == "return_and_refund" else Decimal(item["subtotal"]) * Decimal("0.60")
        rows.append(
            {
                "return_id": f"RET{idx:05d}",
                "order_id": order["order_id"],
                "order_item_id": item["order_item_id"],
                "buyer_id": order_map[order["order_id"]]["buyer_id"],
                "request_type": request_type,
                "reason_type": reason,
                "reason_description": f"Simulated after-sales case: {reason.replace('_', ' ')}.",
                "amount": money(amount),
                "status": status,
                "requested_at": iso(requested),
                "completed_at": iso(completed),
                "is_mock_data": MOCK,
            }
        )
    return rows


def localized_customer_line(language: str, intent: str) -> tuple[str, str]:
    questions = {
        "product_inquiry": "Can you explain the main product features?",
        "size_inquiry": "Which size or variation should I choose?",
        "stock_inquiry": "Is this item currently available?",
        "order_query": "What is the current status of my order?",
        "logistics_query": "Where is my parcel now?",
        "cancel_order": "Can I cancel this order before shipment?",
        "refund_request": "I would like to request a refund. What information is needed?",
        "complaint": "The item did not meet expectations. How can this be resolved?",
        "product_recommendation": "Please recommend a suitable option for everyday use.",
    }
    answers = {
        "product_inquiry": "I can help. The product details and selected variation are available in the mock catalog.",
        "size_inquiry": "Please compare your measurements with the listed variation details before choosing.",
        "stock_inquiry": "I checked the simulated inventory and can confirm the current stock status.",
        "order_query": "I found the simulated order and will summarize its latest status.",
        "logistics_query": "I found the linked mock tracking record and its latest location.",
        "cancel_order": "Cancellation depends on the current order status; shipped orders need manual review.",
        "refund_request": "I can register the request, but approval and refund execution require a human review.",
        "complaint": "I am sorry about the experience. I will record the issue and route higher-risk cases to an agent.",
        "product_recommendation": "Based on the stated need, I can compare available mock products and stock.",
    }
    if language != "English":
        prefix = {
            "Malay": "[Bahasa Melayu] ",
            "Indonesian": "[Bahasa Indonesia] ",
            "Thai": "[ภาษาไทย] ",
            "Vietnamese": "[Tiếng Việt] ",
            "Filipino": "[Filipino] ",
        }[language]
        return prefix + questions[intent], prefix + answers[intent]
    return questions[intent], answers[intent]


def generate_customer_data(
    products: list[dict[str, Any]], orders: list[dict[str, Any]], order_items: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    order_map = {row["order_id"]: row for row in orders}
    first_product = {item["order_id"]: item["product_id"] for item in order_items}
    sessions: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    intents = [
        "product_inquiry", "size_inquiry", "stock_inquiry", "order_query", "logistics_query",
        "cancel_order", "refund_request", "complaint", "product_recommendation",
    ]
    order_list = orders[:]
    RNG.shuffle(order_list)
    for index, order in enumerate(order_list[:100], 1):
        session_id = f"SES{index:05d}"
        language = SITES[order["site"]]["language"]
        intent = RNG.choice(intents)
        risk = "high" if intent in {"refund_request", "complaint"} else ("medium" if intent == "cancel_order" else "low")
        status = choose_weighted([("open", 12), ("resolved", 68), ("transferred_to_human", 20 if risk != "low" else 5)])
        created = datetime.fromisoformat(order["created_at"]) + timedelta(hours=RNG.randint(1, 72))
        sessions.append(
            {
                "session_id": session_id,
                "buyer_id": order["buyer_id"],
                "order_id": order["order_id"],
                "product_id": first_product[order["order_id"]],
                "language": language,
                "intent": intent,
                "risk_level": risk,
                "session_status": status,
                "created_at": iso(created),
                "is_mock_data": MOCK,
            }
        )
        question, answer = localized_customer_line(language, intent)
        turns = RNG.randint(2, 4)
        conversation: list[tuple[str, str]] = [
            ("buyer", question),
            ("assistant", answer),
        ]
        if turns >= 2:
            conversation.extend(
                [
                    ("buyer", question + " Please confirm using the linked record."),
                    ("assistant", answer + " The response is based only on simulated experimental data."),
                ]
            )
        if turns >= 3:
            conversation.extend(
                [
                    ("buyer", "Thank you. Please save this conversation."),
                    ("assistant", "The mock conversation has been saved for testing and demonstration."),
                ]
            )
        if turns == 4:
            conversation.extend(
                [
                    ("buyer", "If the status changes, should I contact support again?"),
                    ("assistant", "Yes. A later test can retrieve the updated mock status through the adapter."),
                ]
            )
        for sender, content in conversation:
            msg_time = created + timedelta(minutes=3 * len([m for m in messages if m["session_id"] == session_id]))
            messages.append(
                {
                    "message_id": f"MSG{len(messages) + 1:07d}",
                    "session_id": session_id,
                    "sender_type": sender,
                    "content": content,
                    "language": language,
                    "message_time": iso(msg_time),
                    "is_mock_data": MOCK,
                }
            )
    return sessions, messages


def generate_trends() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = datetime(2026, 5, 1, tzinfo=TZ)
    patterns = ["growth_low_comp", "high_sales_high_comp", "decline", "seasonal", "price_up_sales_down"]
    for site_idx, site in enumerate(SITES):
        currency = SITES[site]["currency"]
        for cat_idx, (category_id, category_name) in enumerate(CATEGORIES):
            pattern = patterns[(site_idx + cat_idx) % len(patterns)]
            base_price = random_price(currency)
            previous_search: float | None = None
            for day in range(60):
                date = start + timedelta(days=day)
                noise = RNG.uniform(-2.5, 2.5)
                if pattern == "growth_low_comp":
                    search = 38 + day * 0.85 + noise
                    sales = 32 + day * 0.72 + noise
                    competition = 28 + day * 0.08 + noise / 2
                    avg_price = base_price * (1 + day * 0.0008)
                elif pattern == "high_sales_high_comp":
                    search = 78 + math.sin(day / 5) * 6 + noise
                    sales = 82 + math.sin(day / 6) * 5 + noise
                    competition = 84 + math.sin(day / 7) * 3
                    avg_price = base_price * (1 + math.sin(day / 10) * 0.02)
                elif pattern == "decline":
                    search = 86 - day * 0.75 + noise
                    sales = 80 - day * 0.68 + noise
                    competition = 55 - day * 0.12 + noise / 2
                    avg_price = base_price * (1 - day * 0.001)
                elif pattern == "seasonal":
                    search = 58 + math.sin(day / 4.5) * 20 + noise
                    sales = 55 + math.sin((day - 2) / 4.5) * 18 + noise
                    competition = 48 + math.sin(day / 9) * 8
                    avg_price = base_price * (1 + math.sin(day / 8) * 0.035)
                else:
                    search = 68 - day * 0.35 + noise
                    sales = 72 - day * 0.65 + noise
                    competition = 61 + day * 0.12 + noise / 2
                    avg_price = base_price * (1 + day * 0.004)
                search = max(5.0, min(100.0, search))
                sales = max(5.0, min(100.0, sales))
                competition = max(5.0, min(100.0, competition))
                growth = 0.0 if previous_search is None else (search - previous_search) / max(previous_search, 1.0)
                previous_search = search
                rows.append(
                    {
                        "trend_id": f"TREND{len(rows) + 1:07d}",
                        "site": site,
                        "category_id": category_id,
                        "category_name": category_name,
                        "date": date.date().isoformat(),
                        "search_index": f"{search:.2f}",
                        "sales_index": f"{sales:.2f}",
                        "competition_index": f"{competition:.2f}",
                        "average_price": money(avg_price),
                        "growth_rate": f"{growth:.6f}",
                        "is_mock_data": MOCK,
                    }
                )
    return rows


def update_product_metrics(
    products: list[dict[str, Any]], order_items: list[dict[str, Any]], reviews: list[dict[str, Any]]
) -> None:
    quantities: Counter[str] = Counter()
    for item in order_items:
        quantities[item["product_id"]] += int(item["quantity"])
    ratings: dict[str, list[int]] = defaultdict(list)
    for review in reviews:
        ratings[review["product_id"]].append(int(review["rating"]))
    for product in products:
        pid = product["product_id"]
        historical = quantities[pid] * RNG.randint(4, 15) + RNG.randint(10, 120)
        product["sales_count"] = historical
        product["review_count"] = len(ratings[pid])
        product["rating"] = f"{(sum(ratings[pid]) / len(ratings[pid]) if ratings[pid] else 0):.2f}"
        product["favorite_count"] = max(1, int(historical * RNG.uniform(0.10, 0.42)))


FIELDS = {
    "products.csv": ["product_id", "shop_id", "shop_name", "title", "category_id", "category_name", "description", "platform", "site", "source_type", "currency", "price", "cost", "shipping_cost", "sales_count", "rating", "review_count", "favorite_count", "status", "created_at", "updated_at", "collected_at", "is_mock_data"],
    "skus.csv": ["sku_id", "product_id", "seller_sku", "variation_name", "variation_value", "price", "cost", "weight", "status", "created_at", "is_mock_data"],
    "inventory.csv": ["inventory_id", "sku_id", "warehouse_id", "warehouse_name", "available_stock", "reserved_stock", "safety_stock", "stock_status", "updated_at", "is_mock_data"],
    "reviews.csv": ["review_id", "product_id", "sku_id", "order_id", "buyer_id", "rating", "content", "content_zh", "language", "sentiment_hint", "issue_type", "created_at", "is_mock_data"],
    "orders.csv": ["order_id", "shop_id", "buyer_id", "site", "currency", "order_status", "payment_status", "subtotal", "shipping_fee", "discount_amount", "total_amount", "created_at", "paid_at", "shipped_at", "completed_at", "cancelled_at", "is_mock_data"],
    "order_items.csv": ["order_item_id", "order_id", "product_id", "sku_id", "quantity", "unit_price", "subtotal", "is_mock_data"],
    "logistics.csv": ["logistics_id", "order_id", "tracking_number", "carrier", "logistics_status", "origin", "destination", "estimated_delivery_at", "latest_location", "updated_at", "is_mock_data"],
    "logistics_tracks.csv": ["track_id", "tracking_number", "status", "location", "description", "event_time", "is_mock_data"],
    "customer_sessions.csv": ["session_id", "buyer_id", "order_id", "product_id", "language", "intent", "risk_level", "session_status", "created_at", "is_mock_data"],
    "customer_messages.csv": ["message_id", "session_id", "sender_type", "content", "language", "message_time", "is_mock_data"],
    "returns_refunds.csv": ["return_id", "order_id", "order_item_id", "buyer_id", "request_type", "reason_type", "reason_description", "amount", "status", "requested_at", "completed_at", "is_mock_data"],
    "category_trends.csv": ["trend_id", "site", "category_id", "category_name", "date", "search_index", "sales_index", "competition_index", "average_price", "growth_rate", "is_mock_data"],
}


def main() -> int:
    try:
        RNG.seed(SEED)
        products, skus, inventory = generate_products_and_skus()
        orders, order_items = generate_orders(products, skus)
        reviews = generate_reviews(products, skus, orders, order_items)
        logistics, logistics_tracks = generate_logistics(orders)
        returns_refunds = generate_returns(orders, order_items)
        customer_sessions, customer_messages = generate_customer_data(products, orders, order_items)
        category_trends = generate_trends()
        update_product_metrics(products, order_items, reviews)

        datasets = {
            "products.csv": products,
            "skus.csv": skus,
            "inventory.csv": inventory,
            "reviews.csv": reviews,
            "orders.csv": orders,
            "order_items.csv": order_items,
            "logistics.csv": logistics,
            "logistics_tracks.csv": logistics_tracks,
            "customer_sessions.csv": customer_sessions,
            "customer_messages.csv": customer_messages,
            "returns_refunds.csv": returns_refunds,
            "category_trends.csv": category_trends,
        }
        for filename, rows in datasets.items():
            write_csv(filename, rows, FIELDS[filename])
            print(f"[OK] {filename}: {len(rows)} rows")
        print(f"\nGenerated reproducible mock data with seed {SEED} in {OUT_DIR}")
        return 0
    except Exception as exc:
        print(f"[ERROR] Data generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
