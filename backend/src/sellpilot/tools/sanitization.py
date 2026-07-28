import json
import re
from collections.abc import Mapping
from copy import deepcopy

from pydantic import BaseModel, JsonValue

REDACTED = "[REDACTED]"
DEFAULT_SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "token",
        "authorization",
        "cookie",
        "partner_key",
        "jwt",
        "credential",
    }
)


def _normalized_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _sensitive_names(extra_fields: frozenset[str] | set[str]) -> frozenset[str]:
    return frozenset(_normalized_key(item) for item in DEFAULT_SENSITIVE_FIELDS | set(extra_fields))


def _is_sensitive(key: object, sensitive_names: frozenset[str]) -> bool:
    normalized = _normalized_key(key)
    return any(
        name and (normalized == name or normalized.endswith(name)) for name in sensitive_names
    )


def redact_nested(
    value: object,
    *,
    extra_sensitive_fields: frozenset[str] | set[str] = frozenset(),
) -> JsonValue:
    """Return a JSON-safe redacted copy without mutating the business object."""

    sensitive_names = _sensitive_names(extra_sensitive_fields)

    def visit(item: object) -> JsonValue:
        if isinstance(item, BaseModel):
            return visit(item.model_dump(mode="json"))
        if isinstance(item, Mapping):
            return {
                str(key): (
                    REDACTED
                    if child is not None and _is_sensitive(key, sensitive_names)
                    else visit(child)
                )
                for key, child in item.items()
            }
        if isinstance(item, (list, tuple)):
            return [visit(child) for child in item]
        if item is None or isinstance(item, (str, int, float, bool)):
            return item
        return str(item)

    return visit(deepcopy(value))


def audit_summary(
    value: object,
    *,
    extra_sensitive_fields: frozenset[str] | set[str] = frozenset(),
    max_bytes: int,
) -> dict[str, JsonValue]:
    redacted = redact_nested(value, extra_sensitive_fields=extra_sensitive_fields)
    if isinstance(redacted, dict):
        structured: dict[str, JsonValue] = redacted
    else:
        structured = {"value": redacted}
    encoded = json.dumps(
        structured,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) <= max_bytes:
        return structured
    preview = encoded[: max(0, max_bytes - 200)].decode("utf-8", errors="ignore")
    return {
        "truncated": True,
        "original_size_bytes": len(encoded),
        "preview": preview,
    }


def contains_sensitive_values(
    original: object,
    *,
    extra_sensitive_fields: frozenset[str] | set[str] = frozenset(),
) -> bool:
    redacted = redact_nested(original, extra_sensitive_fields=extra_sensitive_fields)
    if isinstance(original, BaseModel):
        original = original.model_dump(mode="json")
    return redacted != original
