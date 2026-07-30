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
# 使用独立且固定种子的随机数生成器：数据有分布差异，但同版本可重复生成。
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

PRODUCT_DESCRIPTION_CONTEXT = {
    "Wireless Earbuds": "The compact charging case keeps the earbuds ready for commuting, calls, study sessions, and everyday listening.",
    "Portable Charger": "Its portable format provides a practical backup power source for commutes, travel days, and time away from a wall outlet.",
    "USB-C Hub": "It expands a compatible laptop or tablet workspace while keeping several everyday connections together in one portable accessory.",
    "Smart Desk Lamp": "The adjustable light and touch operation make it suitable for reading, focused desk work, and bedside use without a complicated setup.",
    "Storage Organizer": "The foldable design helps sort clothing, toys, or household supplies and can be stored more compactly when it is not needed.",
    "Microfiber Towel Set": "The soft, quick-dry fabric suits bathrooms, gyms, and travel bags while remaining easy to wash and reuse.",
    "Aroma Diffuser": "Quiet mist output supports bedrooms, work areas, or relaxation spaces, while the ambient light adds a gentle visual accent.",
    "Vacuum Storage Bags": "The reusable bags reduce the storage volume of suitable clothing or bedding and help organize wardrobes, luggage, and seasonal items.",
    "Facial Cleansing Brush": "The soft silicone contact surface supports a gentle daily cleansing routine and is straightforward to rinse after use.",
    "Hair Styling Brush": "Adjustable heat gives users more control during routine styling, with a brush format intended for convenient at-home handling.",
    "Makeup Organizer": "Clear modular compartments keep frequently used cosmetics visible and separated on a vanity, shelf, or compact counter.",
    "Travel Bottle Set": "The refillable containers keep suitable toiletries divided and easier to organize in a wash bag, gym kit, or carry-on.",
    "Crossbody Bag": "Secure compartments keep daily essentials organized and accessible during commuting, errands, sightseeing, or casual outings.",
    "Polarized Sunglasses": "The lightweight frame is comfortable for commuting and outdoor leisure, while the polarized lenses help reduce distracting glare.",
    "Minimalist Watch": "The clean dial and adjustable strap provide an understated accessory for work, commuting, and casual everyday wear.",
    "Travel Wallet": "Dedicated organization keeps cards and a passport together, while the RFID-blocking construction adds practical protection during travel.",
    "Resistance Band Set": "Different resistance levels support warm-ups and progressive home strength exercises without requiring bulky training equipment.",
    "Insulated Water Bottle": "The double-wall body helps maintain drink temperature during commuting, workouts, desk use, and day trips.",
    "Yoga Mat": "The non-slip surface and included carrying strap support repeat practice at home, in a studio, or during outdoor sessions.",
    "Running Waist Belt": "The sweat-resistant belt keeps a phone and small essentials close to the body during running, walking, or other active use.",
    "Interactive Cat Toy": "Rechargeable motion encourages supervised indoor play and gives cats an engaging activity between owner-led play sessions.",
    "Pet Grooming Brush": "Rounded tips support regular coat care for cats or dogs, and the handheld format makes brushing sessions easier to control.",
    "Slow Feeder Bowl": "The maze layout encourages a slower feeding pace and can be added to a pet's supervised daily mealtime routine.",
    "Portable Pet Bottle": "The leak-resistant bottle keeps drinking water convenient for supervised walks, park visits, road trips, and other outings.",
    "Mini Food Chopper": "The compact bowl handles small preparation tasks such as garlic, herbs, and vegetables while taking up limited counter and storage space.",
    "Digital Kitchen Scale": "The clear display and tare function support repeatable ingredient measurement for cooking, baking, and portion preparation.",
    "Electric Milk Frother": "The handheld shape makes it easy to froth suitable milk or mix beverages at home without occupying much kitchen space.",
    "Sandwich Maker": "The compact non-stick press supports quick breakfasts and simple toasted snacks and is designed for straightforward wipe-down after cooling.",
    "Silicone Feeding Set": "The food-grade set and suction base support supervised mealtimes while making the pieces easy to arrange and clean.",
    "Baby Safety Corner Guards": "Soft transparent guards add cushioning to suitable furniture corners while keeping the room's appearance unobtrusive.",
    "Portable Changing Mat": "The foldable wipe-clean surface and storage pockets keep changing essentials together for supervised care at home or while travelling.",
    "Stroller Organizer": "The universal organizer keeps small care items within reach, and insulated cup holders help separate suitable drinks during supervised outings.",
}


def build_option_guidance(variation_name: str) -> str:
    """Return factual ordering guidance tailored to the available variation field."""

    guidance = {
        "Plug": "Check that the selected plug type matches the socket standard at the place of use",
        "Ports": "Check the selected port configuration and compatibility with the devices to be connected",
        "Capacity": "Check the selected capacity, product dimensions, and suitability for the intended use",
        "Size": "Check the selected size against the intended user, pet, storage space, or carried items as applicable",
        "Pack": "Check the selected pack quantity and the size of the items or area to be covered",
        "Thickness": "Check the selected thickness and product dimensions against the intended training setup",
        "Level": "Check that the selected resistance level is appropriate for the intended exercise and current ability",
        "Style": "Check the selected style, frame dimensions, and fit before ordering",
        "Color": "Check the selected color, product dimensions, and local compatibility requirements where applicable",
    }
    return guidance.get(
        variation_name,
        "Check the selected option and product dimensions before ordering",
    )


def build_product_description(
    product_name: str,
    product_type: str,
    feature_summary: str,
    variation_name: str,
    variations: list[str],
) -> str:
    """Build a detailed, deterministic catalog description for every mock product."""

    feature_text = feature_summary.rstrip(".")
    context = PRODUCT_DESCRIPTION_CONTEXT[product_type]
    option_text = ", ".join(variations)
    guidance = build_option_guidance(variation_name)
    return (
        f"{product_name} - {feature_text}. {context} "
        f"Available {variation_name.lower()} options include {option_text}. "
        f"{guidance}."
    )


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

POSITIVE_ZH = [
    "使用顺畅，做工比预期更结实。",
    "包装整洁，颜色与图片一致，而且容易使用。",
    "日常使用很方便，配送也比预期更快。",
    "做工整洁，尺寸对我来说正合适。",
    "设计很实用，我愿意推荐给朋友。",
]

NEUTRAL = {
    "English": ["It works as described, though the finish is fairly basic.", "Acceptable for the price; delivery took the usual time."],
    "Malay": ["Produk berfungsi seperti diterangkan, tetapi kemasannya biasa sahaja.", "Sesuai dengan harga; masa penghantaran adalah sederhana."],
    "Indonesian": ["Produk berfungsi sesuai deskripsi, tetapi finishing-nya biasa saja.", "Cukup sesuai harga; waktu pengiriman standar."],
    "Thai": ["สินค้าใช้งานได้ตามรายละเอียด แต่งานประกอบค่อนข้างธรรมดา", "คุณภาพเหมาะกับราคา ระยะเวลาจัดส่งปกติ"],
    "Vietnamese": ["Sản phẩm đúng mô tả nhưng phần hoàn thiện khá cơ bản.", "Chất lượng phù hợp với giá, thời gian giao hàng bình thường."],
    "Filipino": ["Gumagana ayon sa description pero simple lang ang finish.", "Katanggap-tanggap sa presyo at normal ang tagal ng delivery."],
}

NEUTRAL_ZH = [
    "功能符合描述，不过做工比较基础。",
    "以这个价格来说可以接受，配送时效也属正常。",
]

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

NEGATIVE_ZH = {
    "product_quality": "商品刚开始可以使用，但整体做工显得不够牢固。",
    "packaging": "商品仍能使用，但收到时外包装已经被压坏。",
    "logistics": "商品本身尚可，但实际送达时间比承诺时间晚了很多。",
    "wrong_item": "收到的款式与下单时选择的款式不一致。",
    "size": "实际尺寸比商品页面标注的尺寸更小。",
    "battery": "电池续航时间明显短于预期。",
    "material": "实物材质比商品页面展示的看起来更薄。",
    "customer_service": "问题并不复杂，但等待明确回复所花的时间太长。",
}

REVIEW_CONTEXT = {
    "English": 'I bought "{title}", {variation_name}: {variation_value}.',
    "Malay": 'Saya membeli "{title}", {variation_name}: {variation_value}.',
    "Indonesian": 'Saya membeli "{title}", {variation_name}: {variation_value}.',
    "Thai": 'ฉันซื้อ "{title}" รุ่น {variation_name}: {variation_value}',
    "Vietnamese": 'Tôi đã mua "{title}", {variation_name}: {variation_value}.',
    "Filipino": 'Binili ko ang "{title}", {variation_name}: {variation_value}.',
}

REVIEW_USAGE_CONTEXTS = {
    "English": [
        "",
        " I tested it for several days before writing this review.",
        " This is based on regular daily use.",
        " I checked the received item against the product listing.",
    ],
    "Malay": [
        "",
        " Saya mengujinya selama beberapa hari sebelum menulis ulasan ini.",
        " Ulasan ini berdasarkan penggunaan harian biasa.",
        " Saya membandingkan barang yang diterima dengan halaman produk.",
    ],
    "Indonesian": [
        "",
        " Saya mencobanya selama beberapa hari sebelum menulis ulasan ini.",
        " Ulasan ini berdasarkan pemakaian sehari-hari.",
        " Saya membandingkan barang yang diterima dengan halaman produk.",
    ],
    "Thai": [
        "",
        " ฉันทดลองใช้หลายวันก่อนเขียนรีวิวนี้",
        " รีวิวนี้มาจากการใช้งานประจำวัน",
        " ฉันตรวจสอบสินค้าที่ได้รับเทียบกับหน้ารายการสินค้า",
    ],
    "Vietnamese": [
        "",
        " Tôi đã dùng thử vài ngày trước khi viết đánh giá này.",
        " Đánh giá này dựa trên quá trình sử dụng hằng ngày.",
        " Tôi đã đối chiếu sản phẩm nhận được với trang sản phẩm.",
    ],
    "Filipino": [
        "",
        " Sinubukan ko ito nang ilang araw bago isinulat ang review na ito.",
        " Batay ang review na ito sa regular na araw-araw na paggamit.",
        " Inihambing ko ang natanggap na item sa product listing.",
    ],
}

REVIEW_USAGE_CONTEXTS_ZH = [
    "",
    "我试用了几天后才写下这条评价。",
    "这条评价基于日常实际使用体验。",
    "我将收到的商品与商品页面进行了核对。",
]

VARIATION_NAME_ZH = {
    "Battery": "电池容量",
    "Capacity": "容量",
    "Color": "颜色",
    "Length": "长度",
    "Pack": "包装数量",
    "Plug": "插头规格",
    "Ports": "接口",
    "Size": "尺寸",
    "Style": "款式",
}

CATEGORY_NEGATIVE_ISSUES = {
    "Consumer Electronics": ["product_quality", "battery", "material", "packaging", "logistics", "wrong_item"],
    "Home & Living": ["product_quality", "material", "size", "packaging", "logistics", "wrong_item"],
    "Beauty & Personal Care": ["product_quality", "material", "packaging", "logistics", "wrong_item", "customer_service"],
    "Fashion Accessories": ["size", "material", "product_quality", "wrong_item", "packaging", "logistics"],
    "Sports & Outdoors": ["size", "material", "product_quality", "packaging", "logistics", "wrong_item"],
    "Pet Supplies": ["size", "material", "product_quality", "packaging", "logistics", "wrong_item"],
    "Kitchen Appliances": ["product_quality", "material", "size", "packaging", "logistics", "wrong_item"],
    "Baby Products": ["material", "product_quality", "size", "packaging", "logistics", "wrong_item"],
}

RATING_PROFILES = {
    "excellent": [(5, 66), (4, 22), (3, 6), (2, 4), (1, 2)],
    "strong": [(5, 46), (4, 31), (3, 12), (2, 7), (1, 4)],
    "mixed": [(5, 27), (4, 27), (3, 19), (2, 16), (1, 11)],
    "weak": [(5, 13), (4, 19), (3, 21), (2, 27), (1, 20)],
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
    """先生成稳定商品 ID，再派生 SKU 与库存，保证三张表引用一致。"""
    products: list[dict[str, Any]] = []
    skus: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    shop_by_site: dict[str, tuple[str, str]] = {}
    for index, site in enumerate(SITES, 1):
        shop_by_site[site] = (f"SHOP{index:03d}", f"Demo {site} Smart Store")

    # 基础实验集固定生成 100 个商品；额外手工草稿不属于本生成器输出。
    for idx in range(1, 101):
        category_id, category = CATEGORIES[(idx - 1) % len(CATEGORIES)]
        site = list(SITES)[(idx - 1) % len(SITES)]
        currency = SITES[site]["currency"]
        shop_id, shop_name = shop_by_site[site]
        product_name, feature_summary, variation_name, variations = RNG.choice(
            CATEGORY_PRODUCTS[category]
        )
        title = f"{product_name} {RNG.choice(['Essential', 'Plus', 'Everyday', 'Compact', 'Premium'])} {idx:03d}"
        description = build_product_description(
            title,
            product_name,
            feature_summary,
            variation_name,
            variations,
        )
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
    """基于已生成的商品和 SKU 创建订单及明细，避免产生孤立业务 ID。"""
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
    skus_by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sku in skus:
        skus_by_product[sku["product_id"]].append(sku)

    for index in range(1, 501):
        order_id = f"ORD{index:06d}"
        coverage_product = products[index - 1] if index <= len(products) else None
        site = coverage_product["site"] if coverage_product else RNG.choice(list(SITES))
        currency = SITES[site]["currency"]
        created = BASE_TIME - timedelta(days=RNG.randint(2, 180), minutes=RNG.randint(0, 1439))
        status = RNG.choice(["delivered", "completed"]) if coverage_product else choose_weighted(statuses)
        item_count = RNG.randint(1, 4)
        if coverage_product:
            required_sku = RNG.choice(skus_by_product[coverage_product["product_id"]])
            optional_skus = [sku for sku in skus_by_site[site] if sku["sku_id"] != required_sku["sku_id"]]
            selected = [required_sku, *RNG.sample(optional_skus, k=item_count - 1)]
        else:
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
    """从有效订单明细派生评论，使评论同时关联商品、SKU、订单和买家。"""
    product_map = {row["product_id"]: row for row in products}
    sku_map = {row["sku_id"]: row for row in skus}
    order_map = {row["order_id"]: row for row in orders}
    eligible_by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in order_items:
        if order_map[item["order_id"]]["order_status"] in {"delivered", "completed", "refund_requested", "refunded"}:
            eligible_by_product[item["product_id"]].append(item)

    missing_products = [product_id for product_id in product_map if not eligible_by_product[product_id]]
    if missing_products:
        raise ValueError(f"Products lack completed-order review sources: {missing_products}")

    # Every product gets a small review baseline. Remaining reviews follow a
    # long-tail popularity profile so counts are intentionally non-uniform.
    review_counts = {product_id: 4 for product_id in product_map}
    popularity = {product_id: RNG.lognormvariate(0.0, 0.85) for product_id in product_map}
    product_ids = list(product_map)
    for product_id in RNG.choices(
        product_ids,
        weights=[popularity[product_id] for product_id in product_ids],
        k=1000 - sum(review_counts.values()),
    ):
        review_counts[product_id] += 1

    # A stable product-level quality profile creates realistic differences
    # between products instead of applying one global average distribution.
    profile_names = list(RATING_PROFILES)
    profile_weights = [14, 38, 32, 16]
    product_profiles = {
        product_id: choose_weighted(list(zip(profile_names, profile_weights)))
        for product_id in product_ids
    }

    reviews: list[dict[str, Any]] = []
    for product_id in product_ids:
        product = product_map[product_id]
        language = SITES[product["site"]]["language"]
        count = review_counts[product_id]
        profile = product_profiles[product_id]

        # Explicitly include both positive and negative experience for every
        # product, then sample the remaining ratings from its own profile.
        ratings = [
            RNG.choice([4, 5]),
            RNG.choice([1, 2]),
            3,
            *[choose_weighted(RATING_PROFILES[profile]) for _ in range(count - 3)],
        ]
        RNG.shuffle(ratings)

        for rating in ratings:
            item = RNG.choice(eligible_by_product[product_id])
            order = order_map[item["order_id"]]
            sku = sku_map[item["sku_id"]]
            context = REVIEW_CONTEXT[language].format(
                title=product["title"],
                variation_name=sku["variation_name"],
                variation_value=sku["variation_value"],
            )
            context_zh = (
                f'我购买的是“{product["title"]}”，'
                f'{VARIATION_NAME_ZH.get(sku["variation_name"], sku["variation_name"])}'
                f'为“{sku["variation_value"]}”。'
            )
            usage_index = RNG.randrange(len(REVIEW_USAGE_CONTEXTS_ZH))
            usage = REVIEW_USAGE_CONTEXTS[language][usage_index]
            usage_zh = REVIEW_USAGE_CONTEXTS_ZH[usage_index]

            if rating >= 4:
                sentiment = "positive"
                issue = "none"
                template_index = RNG.randrange(len(POSITIVE[language]))
                experience = POSITIVE[language][template_index]
                experience_zh = POSITIVE_ZH[template_index]
            elif rating == 3:
                sentiment = "neutral"
                issue = "none"
                template_index = RNG.randrange(len(NEUTRAL[language]))
                experience = NEUTRAL[language][template_index]
                experience_zh = NEUTRAL_ZH[template_index]
            else:
                sentiment = "negative"
                issue = RNG.choice(CATEGORY_NEGATIVE_ISSUES[product["category_name"]])
                experience = NEGATIVE[issue][language]
                experience_zh = NEGATIVE_ZH[issue]

            created = datetime.fromisoformat(order["completed_at"]) + timedelta(
                days=RNG.randint(0, 21),
                hours=RNG.randint(0, 23),
            )
            reviews.append(
                {
                    "review_id": f"REV{len(reviews) + 1:06d}",
                    "product_id": product_id,
                    "sku_id": item["sku_id"],
                    "order_id": item["order_id"],
                    "buyer_id": order["buyer_id"],
                    "rating": rating,
                    "content": f"{context} {experience}{usage}",
                    "content_zh": f"{context_zh}{experience_zh}{usage_zh}",
                    "language": language,
                    "sentiment_hint": sentiment,
                    "issue_type": issue,
                    "created_at": iso(created),
                    "is_mock_data": MOCK,
                }
            )
    RNG.shuffle(reviews)
    for index, review in enumerate(reviews, 1):
        review["review_id"] = f"REV{index:06d}"
    return reviews


def generate_logistics(orders: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """为已进入履约阶段的订单生成物流主记录和按时间递增的轨迹。"""
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
    """从真实存在的订单明细派生售后记录，保持订单、明细和买家一致。"""
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
    """以订单中的首个商品建立客服会话，再用 session_id 串联多轮消息。"""
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
    """从订单明细和评论反算商品销量、评论数与评分，避免指标独立造数。"""
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
        # 每次入口执行前复位种子，避免同一进程重复调用时结果漂移。
        RNG.seed(SEED)
        # 后续数据始终引用前序已生成实体，而不是让各 CSV 独立随机生成。
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
