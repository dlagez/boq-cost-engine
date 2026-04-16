from __future__ import annotations

import argparse
import hashlib
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from db import create_connection

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(slots=True)
class ImportStats:
    single_projects: int = 0
    single_project_profiles: int = 0
    single_project_extras: int = 0
    unit_projects: int = 0
    unit_project_extras: int = 0
    divisions: int = 0
    boq_items: int = 0
    quotas: int = 0
    resource_summaries: int = 0
    resource_usages: int = 0


SINGLE_PROJECT_PROFILE_FIELDS = (
    "工程类型",
    "结构类型",
    "基础类型",
    "主要工程特征",
    "层数",
    "檐高",
)


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
    digest = hashlib.sha1(file_path.read_bytes()).hexdigest()[:16]
    return f"xml-{digest}"


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


def insert_row(cursor: Any, table: str, data: dict[str, Any]) -> int:
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    cursor.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        tuple(data.values()),
    )
    return int(cursor.lastrowid)


def executemany_insert(cursor: Any, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    column_sql = ", ".join(columns)
    placeholder_sql = ", ".join(["%s"] * len(columns))
    cursor.executemany(
        f"INSERT INTO {table} ({column_sql}) VALUES ({placeholder_sql})",
        [tuple(row[column] for column in columns) for row in rows],
    )


def chunked(values: list[int], size: int = 500) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def select_ids(cursor: Any, sql: str, params: tuple[Any, ...]) -> list[int]:
    cursor.execute(sql, params)
    return [int(row["id"]) for row in cursor.fetchall()]


def delete_by_ids(cursor: Any, table: str, column: str, ids: list[int]) -> None:
    if not ids:
        return
    for group in chunked(ids):
        placeholders = ", ".join(["%s"] * len(group))
        cursor.execute(
            f"DELETE FROM {table} WHERE {column} IN ({placeholders})",
            tuple(group),
        )


def cleanup_existing_batch(cursor: Any, batch_no: str) -> None:
    cursor.execute(
        "SELECT id FROM cost_import_batch WHERE batch_no = %s",
        (batch_no,),
    )
    row = cursor.fetchone()
    if not row:
        return

    batch_id = int(row["id"])
    single_project_ids = select_ids(
        cursor,
        "SELECT id FROM cost_single_project WHERE batch_id = %s",
        (batch_id,),
    )
    delete_by_ids(cursor, "cost_single_project_profile", "single_project_id", single_project_ids)
    delete_by_ids(cursor, "cost_single_project_extra", "single_project_id", single_project_ids)

    unit_project_ids: list[int] = []
    if single_project_ids:
        for group in chunked(single_project_ids):
            placeholders = ", ".join(["%s"] * len(group))
            unit_project_ids.extend(
                select_ids(
                    cursor,
                    f"SELECT id FROM cost_unit_project WHERE single_project_id IN ({placeholders})",
                    tuple(group),
                )
            )

    delete_by_ids(cursor, "cost_unit_project_extra", "unit_project_id", unit_project_ids)

    division_ids: list[int] = []
    if unit_project_ids:
        for group in chunked(unit_project_ids):
            placeholders = ", ".join(["%s"] * len(group))
            division_ids.extend(
                select_ids(
                    cursor,
                    f"SELECT id FROM cost_division WHERE unit_project_id IN ({placeholders})",
                    tuple(group),
                )
            )

    boq_item_ids: list[int] = []
    if division_ids:
        for group in chunked(division_ids):
            placeholders = ", ".join(["%s"] * len(group))
            boq_item_ids.extend(
                select_ids(
                    cursor,
                    f"SELECT id FROM cost_boq_item WHERE division_id IN ({placeholders})",
                    tuple(group),
                )
            )

    quota_ids: list[int] = []
    if boq_item_ids:
        for group in chunked(boq_item_ids):
            placeholders = ", ".join(["%s"] * len(group))
            quota_ids.extend(
                select_ids(
                    cursor,
                    f"SELECT id FROM cost_boq_item_quota WHERE boq_item_id IN ({placeholders})",
                    tuple(group),
                )
            )

    delete_by_ids(cursor, "cost_quota_resource_usage", "quota_id", quota_ids)
    delete_by_ids(cursor, "cost_boq_item_quota", "id", quota_ids)
    delete_by_ids(cursor, "cost_boq_item", "id", boq_item_ids)
    delete_by_ids(cursor, "cost_division", "id", division_ids)
    delete_by_ids(cursor, "cost_unit_project", "id", unit_project_ids)
    cursor.execute("DELETE FROM cost_resource_summary WHERE batch_id = %s", (batch_id,))
    cursor.execute("DELETE FROM cost_single_project WHERE batch_id = %s", (batch_id,))
    cursor.execute("DELETE FROM cost_import_batch WHERE id = %s", (batch_id,))


def build_batch_row(root: ET.Element, file_path: Path, batch_no: str) -> dict[str, Any]:
    bid_info = root.find("工程项目投标信息表")
    remark_parts = [
        f"标准版本号={root.attrib.get('标准版本号', '')}",
        f"标准名称={root.attrib.get('标准名称', '')}",
    ]
    if bid_info is not None and bid_info.attrib.get("计价软件名称及版本号"):
        remark_parts.append(f"计价软件={bid_info.attrib['计价软件名称及版本号']}")
    return {
        "batch_no": batch_no,
        "project_name": text_value(root.attrib.get("工程名称"), 255)
        or text_value((bid_info.attrib.get("工程名称") if bid_info is not None else None), 255),
        "source_type": "bid",
        "source_file_name": file_path.name[:255],
        "import_status": "SUCCESS",
        "remark": "; ".join(part for part in remark_parts if part and not part.endswith("="))[:500],
    }


def build_single_project_row(batch_id: int, element: ET.Element) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "seq_no": int_value(element.attrib.get("序号")),
        "single_project_name": text_value(element.attrib.get("单项工程名称"), 255) or "",
        "single_project_cost": decimal_value(element.attrib.get("金额")),
        "division_amount": decimal_value(element.attrib.get("分部分项合计")),
        "measure_amount": decimal_value(element.attrib.get("措施项目合计")),
        "other_amount": decimal_value(element.attrib.get("其他项目合计")),
        "regulation_amount": decimal_value(element.attrib.get("规费合计")),
        "fee_amount": decimal_value(element.attrib.get("费用合计")),
        "tax_amount": decimal_value(element.attrib.get("税金合计")),
        "total_measure_amount": decimal_value(element.attrib.get("总价措施项目合计")),
        "safe_civilized_amount": decimal_value(element.attrib.get("安全文明施工费合计")),
        "provisional_sum_amount": decimal_value(element.attrib.get("暂列金额合计")),
        "material_provisional_amount": decimal_value(element.attrib.get("材料暂估价合计")),
        "specialty_provisional_amount": decimal_value(element.attrib.get("专业工程暂估价合计")),
        "labor_amount": decimal_value(element.attrib.get("人工费合计")),
        "material_amount": decimal_value(element.attrib.get("材料费合计")),
        "machine_amount": decimal_value(element.attrib.get("机械费合计")),
        "equipment_amount": decimal_value(element.attrib.get("设备费合计")),
        "management_amount": decimal_value(element.attrib.get("管理费合计")),
        "profit_amount": decimal_value(element.attrib.get("利润合计")),
        "risk_amount": decimal_value(element.attrib.get("风险费合计")),
        "construction_scale": decimal_value(element.attrib.get("建筑面积")),
        "construction_scale_unit": None,
        "single_project_category_code": text_value(element.attrib.get("单项工程类型"), 32),
        "remark": text_value(element.attrib.get("备注"), 500),
    }


def build_single_project_profiles(single_project_id: int, element: ET.Element) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, field in enumerate(SINGLE_PROJECT_PROFILE_FIELDS, start=1):
        value = text_value(element.attrib.get(field))
        if not value:
            continue
        rows.append(
            {
                "single_project_id": single_project_id,
                "attr_name": field,
                "attr_value": value,
                "sort_no": index,
            }
        )
    return rows


def build_unit_project_row(single_project_id: int, element: ET.Element) -> dict[str, Any]:
    return {
        "single_project_id": single_project_id,
        "unit_project_code": text_value(element.attrib.get("单位工程编码"), 64) or "",
        "unit_project_name": text_value(element.attrib.get("单位工程名称"), 255) or "",
        "unit_project_cost": decimal_value(element.attrib.get("金额")),
        "specialty_category": text_value(element.attrib.get("专业类别"), 64) or "",
        "level3_metric_code": None,
        "division_amount": decimal_value(element.attrib.get("分部分项合计")),
        "measure_amount": decimal_value(element.attrib.get("措施项目合计")),
        "other_amount": decimal_value(element.attrib.get("其他项目合计")),
        "safe_civilized_amount": decimal_value(element.attrib.get("安全文明施工费合计")),
        "regulation_amount": decimal_value(element.attrib.get("规费合计")),
        "fee_amount": decimal_value(element.attrib.get("费用合计")),
        "tax_amount": decimal_value(element.attrib.get("税金合计")),
        "total_measure_amount": decimal_value(element.attrib.get("总价措施项目合计")),
        "provisional_sum_amount": decimal_value(element.attrib.get("暂列金额合计")),
        "material_provisional_amount": decimal_value(element.attrib.get("材料暂估价合计")),
        "specialty_provisional_amount": decimal_value(element.attrib.get("专业工程暂估价合计")),
        "labor_amount": decimal_value(element.attrib.get("人工费合计")),
        "material_amount": decimal_value(element.attrib.get("材料费合计")),
        "machine_amount": decimal_value(element.attrib.get("机械费合计")),
        "equipment_amount": decimal_value(element.attrib.get("设备费合计")),
        "management_amount": decimal_value(element.attrib.get("管理费合计")),
        "profit_amount": decimal_value(element.attrib.get("利润合计")),
        "risk_amount": decimal_value(element.attrib.get("风险费合计")),
        "professional_type_code": None,
        "remark": text_value(element.attrib.get("备注"), 500),
    }


def build_unit_project_extra_rows(unit_project_id: int, element: ET.Element) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, child in enumerate(element.findall("单位工程附加信息表"), start=1):
        name = text_value(child.attrib.get("名称"), 128)
        value = text_value(child.attrib.get("内容"))
        if not name or value is None:
            continue
        rows.append(
            {
                "unit_project_id": unit_project_id,
                "attr_name": name,
                "attr_value": value,
                "sort_no": index,
            }
        )
    return rows


def build_division_row(unit_project_id: int, element: ET.Element, index: int) -> dict[str, Any]:
    raw_code = text_value(element.attrib.get("分部工程编号"), 64)
    division_code = raw_code or f"AUTO-{index:03d}"
    return {
        "unit_project_id": unit_project_id,
        "division_code": division_code,
        "division_name": text_value(element.attrib.get("分部工程名称"), 255) or "",
        "level4_metric_code": None,
        "division_total_amount": decimal_value(element.attrib.get("分部工程合计")),
        "provisional_amount": decimal_value(element.attrib.get("暂估价合计")),
    }


def build_boq_item_row(division_id: int, element: ET.Element) -> dict[str, Any]:
    return {
        "division_id": division_id,
        "seq_no": int_value(element.attrib.get("序号")),
        "item_code": text_value(element.attrib.get("项目编码"), 64) or "",
        "item_name": text_value(element.attrib.get("项目名称"), 255) or "",
        "item_feature_desc": text_value(element.attrib.get("项目特征描述")) or "",
        "measure_unit": text_value(element.attrib.get("计量单位"), 32) or "",
        "quantity": decimal_value(element.attrib.get("工程量")),
        "composite_unit_price": decimal_value(element.attrib.get("综合单价")),
        "composite_amount": decimal_value(element.attrib.get("综合合价")),
        "labor_unit_price": decimal_value(element.attrib.get("人工费单价")),
        "material_unit_price": decimal_value(element.attrib.get("材料费单价")),
        "machine_unit_price": decimal_value(element.attrib.get("机械费单价")),
        "management_unit_price": decimal_value(element.attrib.get("管理费单价")),
        "profit_unit_price": decimal_value(element.attrib.get("利润单价")),
        "risk_unit_price": decimal_value(element.attrib.get("风险费单价")),
        "total_measure_unit_price": decimal_value(element.attrib.get("总价措施单价")),
        "regulation_unit_price": decimal_value(element.attrib.get("规费单价")),
        "fee_unit_price": decimal_value(element.attrib.get("费用单价")),
        "tax_unit_price": decimal_value(element.attrib.get("税金单价")),
        "labor_amount": decimal_value(element.attrib.get("人工费合价")),
        "material_amount": decimal_value(element.attrib.get("材料费合价")),
        "machine_amount": decimal_value(element.attrib.get("机械费合价")),
        "management_amount": decimal_value(element.attrib.get("管理费合价")),
        "profit_amount": decimal_value(element.attrib.get("利润合价")),
        "risk_amount": decimal_value(element.attrib.get("风险费合价")),
        "total_measure_amount": decimal_value(element.attrib.get("总价措施合价")),
        "regulation_amount": decimal_value(element.attrib.get("规费合价")),
        "fee_amount": decimal_value(element.attrib.get("费用合价")),
        "tax_amount": decimal_value(element.attrib.get("税金合价")),
        "professional_type_code": text_value(element.attrib.get("专业类型"), 32) or "",
        "unpriced_material_amount": decimal_value(element.attrib.get("未计价材料合价")),
        "labor_unit_price_desc": text_value(element.attrib.get("人工单价")) or "",
        "provisional_amount": decimal_value(element.attrib.get("暂估合价")),
        "level5_metric_code": None,
        "remark": text_value(element.attrib.get("备注"), 500),
    }


def build_quota_row(boq_item_id: int, element: ET.Element) -> dict[str, Any]:
    return {
        "boq_item_id": boq_item_id,
        "quota_code": text_value(element.attrib.get("定额编号"), 64) or "",
        "quota_name": text_value(element.attrib.get("定额名称"), 255) or "",
        "quota_unit": text_value(element.attrib.get("定额单位"), 32) or "",
        "quantity": decimal_value(element.attrib.get("数量")),
        "labor_unit_price": decimal_value(element.attrib.get("人工费单价")),
        "material_unit_price": decimal_value(element.attrib.get("材料费单价")),
        "machine_unit_price": decimal_value(element.attrib.get("机械费单价")),
        "management_unit_price": decimal_value(element.attrib.get("管理费单价")),
        "profit_unit_price": decimal_value(element.attrib.get("利润单价")),
        "risk_unit_price": decimal_value(element.attrib.get("风险费单价")),
        "total_measure_unit_price": decimal_value(element.attrib.get("总价措施单价")),
        "regulation_unit_price": decimal_value(element.attrib.get("规费单价")),
        "fee_unit_price": decimal_value(element.attrib.get("费用单价")),
        "tax_unit_price": decimal_value(element.attrib.get("税金单价")),
        "composite_unit_price": decimal_value(element.attrib.get("综合单价")),
        "composite_amount": decimal_value(element.attrib.get("综合合价")),
        "labor_amount": decimal_value(element.attrib.get("人工费合价")),
        "material_amount": decimal_value(element.attrib.get("材料费合价")),
        "machine_amount": decimal_value(element.attrib.get("机械费合价")),
        "management_amount": decimal_value(element.attrib.get("管理费合价")),
        "profit_amount": decimal_value(element.attrib.get("利润合价")),
        "risk_amount": decimal_value(element.attrib.get("风险费合价")),
        "total_measure_amount": decimal_value(element.attrib.get("总价措施合价")),
        "regulation_amount": decimal_value(element.attrib.get("规费合价")),
        "fee_total_amount": decimal_value(element.attrib.get("费用合价")),
        "tax_amount": decimal_value(element.attrib.get("税金合价")),
        "unpriced_material_amount": decimal_value(element.attrib.get("未计价材料合价")),
        "provisional_unit_price": decimal_value(element.attrib.get("暂估单价")),
        "provisional_amount": decimal_value(element.attrib.get("暂估合价")),
        "professional_type_code": text_value(element.attrib.get("专业类型"), 32) or "",
        "remark": text_value(element.attrib.get("备注"), 500),
    }


def collect_resource_summaries(root: ET.Element, batch_id: int) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for element in root.findall(".//工料机汇总表"):
        resource_id = text_value(element.attrib.get("工料机ID"), 64)
        if not resource_id or resource_id in deduped:
            continue
        deduped[resource_id] = {
            "batch_id": batch_id,
            "resource_type": map_resource_type(element.attrib.get("材料类别")),
            "resource_code": text_value(element.attrib.get("材料编码"), 64),
            "resource_name": text_value(element.attrib.get("名称"), 255) or "",
            "resource_unit": text_value(element.attrib.get("单位"), 32),
            "unit_price": decimal_value(element.attrib.get("单价"), default=None),  # type: ignore[arg-type]
            "remark": build_resource_remark(element.attrib),
        }
    return list(deduped.values())


def insert_resource_summaries(
    cursor: Any,
    root: ET.Element,
    batch_id: int,
) -> dict[str, int]:
    rows = collect_resource_summaries(root, batch_id)
    executemany_insert(cursor, "cost_resource_summary", rows)

    resource_map: dict[str, int] = {}
    cursor.execute(
        "SELECT id, resource_code, resource_name, resource_unit, unit_price, remark "
        "FROM cost_resource_summary WHERE batch_id = %s ORDER BY id",
        (batch_id,),
    )
    inserted_rows = cursor.fetchall()

    deduped_ids = [
        text_value(element.attrib.get("工料机ID"), 64)
        for element in root.findall(".//工料机汇总表")
        if text_value(element.attrib.get("工料机ID"), 64)
    ]
    seen: set[str] = set()
    ordered_unique_ids = []
    for resource_id in deduped_ids:
        if resource_id in seen:
            continue
        seen.add(resource_id)
        ordered_unique_ids.append(resource_id)

    for resource_id, row in zip(ordered_unique_ids, inserted_rows, strict=True):
        resource_map[resource_id] = int(row["id"])
    return resource_map


def import_xml_file(file_path: Path) -> tuple[str, ImportStats]:
    batch_no = build_batch_no(file_path)
    stats = ImportStats()
    root = ET.parse(file_path).getroot()

    with create_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cleanup_existing_batch(cursor, batch_no)
                batch_id = insert_row(cursor, "cost_import_batch", build_batch_row(root, file_path, batch_no))
                resource_summary_map = insert_resource_summaries(cursor, root, batch_id)
                stats.resource_summaries = len(resource_summary_map)

                for single_project_element in root.findall("单项工程基本信息表"):
                    single_project_id = insert_row(
                        cursor,
                        "cost_single_project",
                        build_single_project_row(batch_id, single_project_element),
                    )
                    stats.single_projects += 1

                    profile_rows = build_single_project_profiles(single_project_id, single_project_element)
                    executemany_insert(cursor, "cost_single_project_profile", profile_rows)
                    stats.single_project_profiles += len(profile_rows)

                    for unit_project_element in single_project_element.findall("单位工程基本信息表"):
                        unit_project_id = insert_row(
                            cursor,
                            "cost_unit_project",
                            build_unit_project_row(single_project_id, unit_project_element),
                        )
                        stats.unit_projects += 1

                        unit_extra_rows = build_unit_project_extra_rows(unit_project_id, unit_project_element)
                        executemany_insert(cursor, "cost_unit_project_extra", unit_extra_rows)
                        stats.unit_project_extras += len(unit_extra_rows)

                        division_parent = unit_project_element.find("分部分项")
                        if division_parent is None:
                            continue

                        for division_index, division_element in enumerate(
                            division_parent.findall("分部分项信息表"),
                            start=1,
                        ):
                            division_id = insert_row(
                                cursor,
                                "cost_division",
                                build_division_row(unit_project_id, division_element, division_index),
                            )
                            stats.divisions += 1

                            for boq_item_element in division_element.findall("分部分项工程量清单与计价表"):
                                boq_item_id = insert_row(
                                    cursor,
                                    "cost_boq_item",
                                    build_boq_item_row(division_id, boq_item_element),
                                )
                                stats.boq_items += 1

                                for quota_element in boq_item_element.findall("分部分项工程量清单项目子目组价表"):
                                    quota_id = insert_row(
                                        cursor,
                                        "cost_boq_item_quota",
                                        build_quota_row(boq_item_id, quota_element),
                                    )
                                    stats.quotas += 1

                                    usage_rows: list[dict[str, Any]] = []
                                    for usage_element in quota_element.findall("工料机含量表"):
                                        xml_resource_id = text_value(usage_element.attrib.get("汇总材料ID"), 64)
                                        if not xml_resource_id:
                                            continue
                                        resource_summary_id = resource_summary_map.get(xml_resource_id)
                                        if resource_summary_id is None:
                                            continue
                                        usage_rows.append(
                                            {
                                                "quota_id": quota_id,
                                                "resource_summary_id": resource_summary_id,
                                                "consumption_quota_content": decimal_value(
                                                    usage_element.attrib.get("消耗量定额含量")
                                                ),
                                                "consumption_adjust_coef": decimal_value(
                                                    usage_element.attrib.get("消耗量定额含量调整系数"),
                                                    default=ONE,
                                                ),
                                            }
                                        )
                                    executemany_insert(cursor, "cost_quota_resource_usage", usage_rows)
                                    stats.resource_usages += len(usage_rows)

            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return batch_no, stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import cost XML data into MySQL.")
    parser.add_argument("xml_file", type=Path, help="Path to the XML file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    batch_no, stats = import_xml_file(args.xml_file)
    print(f"Imported batch: {batch_no}")
    print(
        "single_projects={single_projects}, profiles={single_project_profiles}, "
        "unit_projects={unit_projects}, unit_extras={unit_project_extras}, "
        "divisions={divisions}, boq_items={boq_items}, quotas={quotas}, "
        "resource_summaries={resource_summaries}, resource_usages={resource_usages}".format(
            **asdict(stats)
        )
    )


if __name__ == "__main__":
    main()
