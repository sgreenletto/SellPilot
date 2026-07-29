import json
import re
from typing import Any

import httpx
from pydantic import ValidationError

from sellpilot.core.config import Settings
from sellpilot.domain.content_generation.models import ListingFacts, LocalizedListing

LOCALIZED_COPY = {
    "en": {
        "product": "Product",
        "category": "Category",
        "audience": "For",
        "specifications": "Specifications",
        "verified": "Verified product facts",
        "designed": "Designed for {site} shoppers",
        "source": "Original product description",
        "marketing": "Explore {product} with clearly stated verified specifications.",
        "question": "Which specifications are included?",
        "answer": "Refer to the verified product facts.",
    },
    "zh-CN": {
        "product": "商品",
        "category": "类目",
        "audience": "适合",
        "specifications": "规格信息",
        "verified": "已核验商品事实",
        "designed": "面向 {site} 站点消费者",
        "source": "商品原始描述",
        "marketing": "了解 {product}，商品信息均基于已核验事实清晰呈现。",
        "question": "商品包含哪些规格信息？",
        "answer": "请参阅已核验的商品事实。",
    },
    "zh-TW": {
        "product": "商品",
        "category": "類目",
        "audience": "適合",
        "specifications": "規格資訊",
        "verified": "已核驗商品事實",
        "designed": "面向 {site} 站點消費者",
        "source": "商品原始描述",
        "marketing": "瞭解 {product}，商品資訊均依據已核驗事實清楚呈現。",
        "question": "商品包含哪些規格資訊？",
        "answer": "請參閱已核驗的商品事實。",
    },
    "ms": {
        "product": "Produk",
        "category": "Kategori",
        "audience": "Untuk",
        "specifications": "Spesifikasi",
        "verified": "Fakta produk yang disahkan",
        "designed": "Direka untuk pembeli {site}",
        "source": "Penerangan produk asal",
        "marketing": "Terokai {product} dengan spesifikasi yang disahkan dan jelas.",
        "question": "Apakah spesifikasi yang disertakan?",
        "answer": "Rujuk fakta produk yang telah disahkan.",
    },
    "id": {
        "product": "Produk",
        "category": "Kategori",
        "audience": "Untuk",
        "specifications": "Spesifikasi",
        "verified": "Fakta produk terverifikasi",
        "designed": "Dirancang untuk pembeli {site}",
        "source": "Deskripsi produk asli",
        "marketing": "Temukan {product} dengan spesifikasi terverifikasi yang jelas.",
        "question": "Spesifikasi apa saja yang disertakan?",
        "answer": "Lihat fakta produk yang telah diverifikasi.",
    },
    "th": {
        "product": "สินค้า",
        "category": "หมวดหมู่",
        "audience": "เหมาะสำหรับ",
        "specifications": "ข้อมูลจำเพาะ",
        "verified": "ข้อมูลสินค้าที่ตรวจสอบแล้ว",
        "designed": "ออกแบบสำหรับผู้ซื้อใน {site}",
        "source": "คำอธิบายสินค้าต้นฉบับ",
        "marketing": "พบกับ {product} พร้อมข้อมูลจำเพาะที่ตรวจสอบแล้วอย่างชัดเจน",
        "question": "สินค้ามีข้อมูลจำเพาะใดบ้าง?",
        "answer": "โปรดดูข้อมูลสินค้าที่ตรวจสอบแล้ว",
    },
    "vi": {
        "product": "Sản phẩm",
        "category": "Danh mục",
        "audience": "Dành cho",
        "specifications": "Thông số kỹ thuật",
        "verified": "Thông tin sản phẩm đã xác minh",
        "designed": "Dành cho người mua tại {site}",
        "source": "Mô tả sản phẩm gốc",
        "marketing": "Khám phá {product} với thông số đã xác minh và trình bày rõ ràng.",
        "question": "Sản phẩm có những thông số nào?",
        "answer": "Vui lòng xem thông tin sản phẩm đã được xác minh.",
    },
    "tl": {
        "product": "Produkto",
        "category": "Kategorya",
        "audience": "Para sa",
        "specifications": "Mga detalye",
        "verified": "Na-verify na impormasyon ng produkto",
        "designed": "Para sa mga mamimili sa {site}",
        "source": "Orihinal na paglalarawan",
        "marketing": "Tuklasin ang {product} na may malinaw at na-verify na mga detalye.",
        "question": "Anong mga detalye ang kasama?",
        "answer": "Tingnan ang na-verify na impormasyon ng produkto.",
    },
    "pt-BR": {
        "product": "Produto",
        "category": "Categoria",
        "audience": "Para",
        "specifications": "Especificações",
        "verified": "Dados verificados do produto",
        "designed": "Desenvolvido para compradores de {site}",
        "source": "Descrição original do produto",
        "marketing": "Conheça {product} com especificações verificadas e apresentadas com clareza.",
        "question": "Quais especificações estão incluídas?",
        "answer": "Consulte os dados verificados do produto.",
    },
}

OPERATOR_KEYWORD_TRANSLATIONS = {
    "laptop": "笔记本",
    "notebook": "笔记本",
    "tablet": "平板",
    "affordable": "实惠",
    "budget": "经济型",
    "compact": "便携",
    "portable": "便携",
    "multi-port": "多接口",
    "multiport": "多接口",
    "productivity": "办公",
    "hub": "扩展坞",
    "dock": "扩展坞",
    "adapter": "转接器",
    "station": "工作站",
    "docking": "扩展",
}
OPERATOR_FACTUAL_MARKERS = (
    "容量",
    "功率",
    "材质",
    "认证",
    "保修",
    "防水",
    "续航",
)


def _operator_keyword_suggestions(suggestions: list[str], facts: ListingFacts) -> list[str]:
    source = " ".join(
        [
            facts.title,
            facts.description,
            *facts.specifications.keys(),
            *facts.specifications.values(),
            *[
                str(value)
                for item in facts.sku_facts
                for value in item.values()
                if value is not None
            ],
        ]
    ).casefold()
    normalized_source = re.sub(r"[\W_]+", "", source)

    def is_supported(value: str) -> bool:
        normalized = re.sub(r"[\W_]+", "", value.casefold())
        return not any(marker in normalized for marker in OPERATOR_FACTUAL_MARKERS) or (
            normalized in normalized_source
        )

    result: list[str] = [
        item.strip()
        for item in facts.requested_keywords
        if item.strip() and re.search(r"[\u3400-\u9fff]", item) and is_supported(item)
    ]
    technical = re.compile(r"^(?:usb-[ac]|usb|hdmi|pd|sd|micro\s*sd|\d+(?:-in-1|合1))$", re.I)
    for suggestion in suggestions:
        value = suggestion.strip()
        if not value:
            continue
        if not is_supported(value):
            continue
        if re.search(r"[\u3400-\u9fff]", value) or technical.fullmatch(value):
            result.append(value)
            continue
        if value.casefold() in source:
            result.append(value)
            continue
        translated: list[str] = []
        unknown = False
        for token in re.findall(r"usb-[ac]|[a-z]+(?:-[a-z]+)?|\d+(?:-in-1)?", value.lower()):
            if technical.fullmatch(token):
                translated.append(token.upper() if token.startswith("usb") else token)
            elif token in OPERATOR_KEYWORD_TRANSLATIONS:
                translated.append(OPERATOR_KEYWORD_TRANSLATIONS[token])
            else:
                unknown = True
                break
        if translated and not unknown:
            result.append("".join(translated))
    return list(dict.fromkeys(result))[:30]


class OfflineTemplateGateway:
    """Deterministic offline provider. It never claims to be a real model call."""

    provider = "offline_template"
    model_name = "sellpilot-localized-template-v1"
    generation_mode = "offline_template"
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0

    async def generate(
        self, facts: ListingFacts, issues: list[str] | None = None
    ) -> LocalizedListing:
        copy = LOCALIZED_COPY.get(facts.target_language, LOCALIZED_COPY["en"])
        spec_text = " · ".join(f"{key}: {value}" for key, value in facts.specifications.items())
        verified_facts = spec_text or copy["answer"]
        base = facts.title.strip()
        language = facts.target_language
        title_keyword = next(
            (
                item
                for item in facts.requested_keywords
                if item.strip() and item.lower() not in base.lower()
            ),
            "",
        )
        title_parts = [base, title_keyword, facts.category_name]
        bullets = [
            f"{copy['product']}：{base}",
            f"{copy['category']}：{facts.category_name}",
            f"{copy['specifications']}: {verified_facts}",
            f"{copy['audience']}：{facts.audience}",
            copy["designed"].format(site=facts.site.upper()),
            *facts.selling_points[: (2 if facts.requested_keywords else 3)],
        ]
        keywords: list[str] = []
        seen_keywords: set[str] = set()
        localized_keyword_seeds = (
            [
                *facts.requested_keywords,
                *facts.selling_points,
                f"{copy['category']} {facts.category_name}",
                f"{copy['product']} {base}",
            ]
            if language in {"zh-CN", "zh-TW"}
            else [
                *facts.requested_keywords,
                facts.category_name,
                base.split(" ")[0],
                language,
            ]
        )
        for item in localized_keyword_seeds:
            normalized_keyword = item.strip().casefold()
            if normalized_keyword and normalized_keyword not in seen_keywords:
                keywords.append(item.strip())
                seen_keywords.add(normalized_keyword)
        listing = LocalizedListing(
            title=" | ".join(item for item in title_parts if item)[:120],
            bullet_points=bullets,
            description=(
                f"{copy['source']}：{facts.description}\n\n{copy['verified']}：{verified_facts}"
            ),
            marketing_copy=copy["marketing"].format(product=base),
            faq=[
                {
                    "question": copy["question"],
                    "answer": spec_text or copy["answer"],
                }
            ],
            sku_content=[
                {
                    "sku": str(item.get("seller_sku") or item.get("external_id", "")),
                    "description": str(
                        item.get("name")
                        or item.get("variation_value")
                        or item.get("seller_sku")
                        or item.get("external_id")
                    ),
                }
                for item in facts.sku_facts
            ],
            keywords=keywords,
            keyword_suggestions_zh=list(
                dict.fromkeys(
                    [
                        *facts.requested_keywords,
                        *[
                            item
                            for item in facts.selling_points
                            if re.search(r"[\u3400-\u9fff]", item)
                        ],
                        f"商品型号 {base}",
                        f"商品类目 {facts.category_name}",
                    ]
                )
            ),
            target_language=language,
            generation_mode=self.generation_mode,
        )
        return listing.model_copy(
            update={
                "keyword_suggestions_zh": _operator_keyword_suggestions(
                    listing.keyword_suggestions_zh,
                    facts,
                )
            }
        )


class ModelGatewayError(RuntimeError):
    """Safe model-provider error that never includes credentials or response bodies."""


class BailianModelGateway:
    """Aliyun Bailian OpenAI-compatible structured-output gateway."""

    provider = "aliyun_bailian"
    generation_mode = "aliyun_bailian"

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if settings.content_model_provider != "aliyun_bailian":
            raise ValueError("Bailian gateway requires aliyun_bailian provider mode")
        assert settings.bailian_api_key is not None
        assert settings.bailian_base_url is not None
        self.model_name = settings.bailian_model
        self._api_key = settings.bailian_api_key.get_secret_value()
        self._base_url = settings.bailian_base_url.rstrip("/")
        self._timeout = settings.bailian_timeout_seconds
        self._transport = transport
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    async def generate(
        self, facts: ListingFacts, issues: list[str] | None = None
    ) -> LocalizedListing:
        schema = LocalizedListing.model_json_schema()
        verified_facts = {
            "product_id": facts.product_id,
            "title": facts.title,
            "description": facts.description,
            "category_name": facts.category_name,
            "specifications": facts.specifications,
            "sku_facts": facts.sku_facts,
        }
        prompt = {
            "task": (
                "Return one JSON object matching the supplied JSON Schema. "
                "Use only verified facts. Never invent prices, quantities, dimensions, "
                "materials, certifications, guarantees, stock, compatibility, protocols, "
                "port breakdowns, test results or performance claims. Preserve every "
                "specification value, allowing only a semantically identical localized form "
                "(for example 6-in-1 may be written as 6合1). If a detail is not present in "
                "verified_facts, omit it or explicitly say it is not provided. "
                "Write all natural-language copy in target_language. Keep the title within "
                "120 characters. Use requested keywords naturally, include a relevant requested "
                "keyword in the title when supplied, and never repeat a keyword more than five "
                "times. Return unique, relevant keywords in target_language; only brand names, "
                "model numbers and technical standards such as USB-C or HDMI may remain "
                "untranslated. Fill keyword_suggestions_zh with concise Simplified Chinese "
                "suggestions for Chinese operators regardless of target_language; only exact "
                "brand names, product models, SKU values and technical standards from verified "
                "facts may remain untranslated there. Include every requested keyword verbatim "
                "in keyword_suggestions_zh, and express its localized target-market equivalent "
                "in keywords and naturally in the title. Target audience, selling points and "
                "keywords are creative directions, not facts."
            ),
            "verified_facts": verified_facts,
            "creative_direction": {
                "site": facts.site,
                "target_language": facts.target_language,
                "audience": facts.audience,
                "selling_points": facts.selling_points,
                "requested_keywords": facts.requested_keywords,
            },
            "previous_validation_issues": issues or [],
            "json_schema": schema,
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate localized ecommerce listings. Output valid JSON only. "
                        "The generation_mode field must be aliyun_bailian."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=False),
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                body: dict[str, Any] = response.json()
            usage = body.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or prompt_tokens + completion_tokens)
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            parsed["generation_mode"] = self.generation_mode
            listing = LocalizedListing.model_validate(parsed)
            return listing.model_copy(
                update={
                    "keyword_suggestions_zh": _operator_keyword_suggestions(
                        listing.keyword_suggestions_zh,
                        facts,
                    )
                }
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise ModelGatewayError("Aliyun Bailian request or response was invalid") from None
        except ValidationError:
            raise ModelGatewayError(
                "Aliyun Bailian output failed the LocalizedListing schema"
            ) from None


def build_model_gateway(settings: Settings) -> OfflineTemplateGateway | BailianModelGateway:
    if settings.content_model_provider == "aliyun_bailian":
        return BailianModelGateway(settings)
    return OfflineTemplateGateway()


async def translate_review_batch(
    settings: Settings,
    reviews: list[tuple[str, str]],
    *,
    target_language: str = "zh-CN",
) -> dict[str, str]:
    """Translate review text with Bailian; never invent a translation in offline mode."""
    if settings.content_model_provider != "aliyun_bailian" or not reviews:
        return {}
    api_key = settings.bailian_api_key.get_secret_value() if settings.bailian_api_key else ""
    if not api_key or not settings.bailian_base_url:
        return {}
    payload = {
        "model": settings.bailian_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Translate ecommerce reviews faithfully. Return JSON only as "
                    '{"translations":[{"review_id":"...","text":"..."}]}. '
                    "Do not summarize, classify, add facts, or remove complaints."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "target_language": target_language,
                        "reviews": [
                            {"review_id": review_id, "text": text} for review_id, text in reviews
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=settings.bailian_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.bailian_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
            parsed = json.loads(body["choices"][0]["message"]["content"])
            allowed = {review_id for review_id, _ in reviews}
            return {
                str(item["review_id"]): str(item["text"]).strip()
                for item in parsed.get("translations", [])
                if str(item.get("review_id")) in allowed and str(item.get("text", "")).strip()
            }
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
            if attempt == 1:
                return {}
    return {}


def build_selection_explanation_generator(settings: Settings):
    if settings.content_model_provider != "aliyun_bailian":
        return None

    async def generate(score: dict[str, object]) -> dict[str, object]:
        api_key = settings.bailian_api_key.get_secret_value() if settings.bailian_api_key else ""
        expected = {
            "total_score": str(score["total_score"]),
            "profit": str(score["profit"]["profit"]),
            "margin": str(score["profit"]["margin"]),
            "data_completeness": str(score["data_completeness"]),
        }
        payload = {
            "model": settings.bailian_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Explain deterministic product selection results. Return JSON only "
                        "with summary, evidence, risks and generation_mode. Evidence must "
                        "contain exactly the supplied metric values; never change a score. "
                        "Write summary and risks in Simplified Chinese."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "expected_evidence": expected,
                            "recommendation_facts": score["recommendation_facts"],
                            "risk_warnings": score["risk_warnings"],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=settings.bailian_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.bailian_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            return json.loads(response.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
            return {}

    return generate
