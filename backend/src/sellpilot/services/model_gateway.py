import json
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
        bullets = [
            f"{copy['product']}：{base}",
            f"{copy['category']}：{facts.category_name}",
            f"{copy['specifications']}: {verified_facts}",
            f"{copy['audience']}：{facts.audience}",
            copy["designed"].format(site=facts.site.upper()),
            *facts.selling_points[: (2 if facts.requested_keywords else 3)],
            *([" · ".join(facts.requested_keywords)] if facts.requested_keywords else []),
        ]
        keywords = list(
            dict.fromkeys(
                [
                    *facts.requested_keywords,
                    facts.category_name,
                    base.split(" ")[0],
                    language,
                ]
            )
        )
        return LocalizedListing(
            title=f"{base} | {facts.category_name}"[:200],
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
            target_language=language,
            generation_mode=self.generation_mode,
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
                "Target audience, selling points and keywords are creative directions, not facts."
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
            return LocalizedListing.model_validate(parsed)
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
