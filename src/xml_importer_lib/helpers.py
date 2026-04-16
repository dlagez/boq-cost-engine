from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

ZERO = Decimal("0")
ONE = Decimal("1")


def decimal_value(raw: str | None, default: Decimal | None = ZERO) -> Decimal | None:
    if raw is None:
        return default
    value = raw.strip()
    if not value:
        return default
    try:
        return Decimal(value)
    except InvalidOperation:
        return default


def int_value(raw: str | None, default: int = 0) -> int:
    if raw is None:
        return default
    value = raw.strip()
    if not value:
        return default
    try:
        return int(Decimal(value))
    except (InvalidOperation, ValueError):
        return default


def text_value(raw: str | None, max_length: int | None = None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    if max_length is not None:
        return value[:max_length]
    return value


def build_batch_no(file_path: Path) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    suffix = uuid4().hex[:8]
    return f"xml-{timestamp}-{suffix}"


def map_resource_type(category_code: str | None) -> str:
    mapping = {
        "1": "labor",
        "2": "material",
        "3": "machine",
        "5": "equipment",
        "7": "machine",
    }
    return mapping.get((category_code or "").strip(), "other")


def build_resource_remark(attrs: dict[str, str]) -> str | None:
    parts: list[str] = []
    spec = text_value(attrs.get("规格型号"), 120)
    if spec:
        parts.append(f"规格型号={spec}")
    if text_value(attrs.get("主要材料标记")) == "true":
        parts.append("主要材料")
    if text_value(attrs.get("暂估材料标记")) == "true":
        parts.append("暂估材料")
    if text_value(attrs.get("评标材料标记")) == "true":
        parts.append("评标材料")
    if text_value(attrs.get("甲供材料标记")) == "true":
        parts.append("甲供材料")
    delivery = text_value(attrs.get("交货方式"), 80)
    if delivery:
        parts.append(f"交货方式={delivery}")
    location = text_value(attrs.get("送达地点"), 80)
    if location:
        parts.append(f"送达地点={location}")
    if not parts:
        return None
    return "; ".join(parts)[:500]
