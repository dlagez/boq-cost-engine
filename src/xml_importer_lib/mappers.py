from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from .helpers import build_resource_remark, decimal_value, int_value, map_resource_type, text_value
from .models import SINGLE_PROJECT_PROFILE_FIELDS


def build_batch_row(root: ET.Element, file_path: Path, batch_no: str) -> tuple[Any, ...]:
    bid_info = root.find("工程项目投标信息表")
    remark_parts = [
        f"标准版本号={root.attrib.get('标准版本号', '')}",
        f"标准名称={root.attrib.get('标准名称', '')}",
    ]
    if bid_info is not None and bid_info.attrib.get("计价软件名称及版本号"):
        remark_parts.append(f"计价软件={bid_info.attrib['计价软件名称及版本号']}")
    return (
        batch_no,
        text_value(root.attrib.get("工程名称"), 255)
        or text_value((bid_info.attrib.get("工程名称") if bid_info is not None else None), 255),
        "bid",
        file_path.name[:255],
        "SUCCESS",
        "; ".join(part for part in remark_parts if part and not part.endswith("="))[:500],
    )


def build_single_project_row(batch_id: int, element: ET.Element) -> tuple[Any, ...]:
    return (
        batch_id,
        int_value(element.attrib.get("序号")),
        text_value(element.attrib.get("单项工程名称"), 255) or "",
        decimal_value(element.attrib.get("金额")),
        decimal_value(element.attrib.get("分部分项合计")),
        decimal_value(element.attrib.get("措施项目合计")),
        decimal_value(element.attrib.get("其他项目合计")),
        decimal_value(element.attrib.get("规费合计")),
        decimal_value(element.attrib.get("费用合计")),
        decimal_value(element.attrib.get("税金合计")),
        decimal_value(element.attrib.get("总价措施项目合计")),
        decimal_value(element.attrib.get("安全文明施工费合计")),
        decimal_value(element.attrib.get("暂列金额合计")),
        decimal_value(element.attrib.get("材料暂估价合计")),
        decimal_value(element.attrib.get("专业工程暂估价合计")),
        decimal_value(element.attrib.get("人工费合计")),
        decimal_value(element.attrib.get("材料费合计")),
        decimal_value(element.attrib.get("机械费合计")),
        decimal_value(element.attrib.get("设备费合计")),
        decimal_value(element.attrib.get("管理费合计")),
        decimal_value(element.attrib.get("利润合计")),
        decimal_value(element.attrib.get("风险费合计")),
        decimal_value(element.attrib.get("建筑面积")),
        None,
        text_value(element.attrib.get("单项工程类型"), 32),
        text_value(element.attrib.get("备注"), 500),
    )


def build_single_project_profiles(single_project_id: int, element: ET.Element) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for index, field in enumerate(SINGLE_PROJECT_PROFILE_FIELDS, start=1):
        value = text_value(element.attrib.get(field))
        if not value:
            continue
        rows.append((single_project_id, field, value, index))
    return rows


def build_unit_project_row(single_project_id: int, element: ET.Element) -> tuple[Any, ...]:
    return (
        single_project_id,
        text_value(element.attrib.get("单位工程编码"), 64) or "",
        text_value(element.attrib.get("单位工程名称"), 255) or "",
        decimal_value(element.attrib.get("金额")),
        text_value(element.attrib.get("专业类别"), 64) or "",
        None,
        decimal_value(element.attrib.get("分部分项合计")),
        decimal_value(element.attrib.get("措施项目合计")),
        decimal_value(element.attrib.get("其他项目合计")),
        decimal_value(element.attrib.get("安全文明施工费合计")),
        decimal_value(element.attrib.get("规费合计")),
        decimal_value(element.attrib.get("费用合计")),
        decimal_value(element.attrib.get("税金合计")),
        decimal_value(element.attrib.get("总价措施项目合计")),
        decimal_value(element.attrib.get("暂列金额合计")),
        decimal_value(element.attrib.get("材料暂估价合计")),
        decimal_value(element.attrib.get("专业工程暂估价合计")),
        decimal_value(element.attrib.get("人工费合计")),
        decimal_value(element.attrib.get("材料费合计")),
        decimal_value(element.attrib.get("机械费合计")),
        decimal_value(element.attrib.get("设备费合计")),
        decimal_value(element.attrib.get("管理费合计")),
        decimal_value(element.attrib.get("利润合计")),
        decimal_value(element.attrib.get("风险费合计")),
        None,
        text_value(element.attrib.get("备注"), 500),
    )


def build_unit_project_extra_rows(unit_project_id: int, element: ET.Element) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for index, child in enumerate(element.findall("单位工程附加信息表"), start=1):
        name = text_value(child.attrib.get("名称"), 128)
        value = text_value(child.attrib.get("内容"))
        if not name or value is None:
            continue
        rows.append((unit_project_id, name, value, index))
    return rows


def build_division_row(unit_project_id: int, element: ET.Element, index: int) -> tuple[Any, ...]:
    raw_code = text_value(element.attrib.get("分部工程编号"), 64)
    division_code = raw_code or f"AUTO-{index:03d}"
    return (
        unit_project_id,
        division_code,
        text_value(element.attrib.get("分部工程名称"), 255) or "",
        None,
        decimal_value(element.attrib.get("分部工程合计")),
        decimal_value(element.attrib.get("暂估价合计")),
    )


def build_boq_item_row(division_id: int, element: ET.Element) -> tuple[Any, ...]:
    return (
        division_id,
        int_value(element.attrib.get("序号")),
        text_value(element.attrib.get("项目编码"), 64) or "",
        text_value(element.attrib.get("项目名称"), 255) or "",
        text_value(element.attrib.get("项目特征描述")) or "",
        text_value(element.attrib.get("计量单位"), 32) or "",
        decimal_value(element.attrib.get("工程量")),
        decimal_value(element.attrib.get("综合单价")),
        decimal_value(element.attrib.get("综合合价")),
        decimal_value(element.attrib.get("人工费单价")),
        decimal_value(element.attrib.get("材料费单价")),
        decimal_value(element.attrib.get("机械费单价")),
        decimal_value(element.attrib.get("管理费单价")),
        decimal_value(element.attrib.get("利润单价")),
        decimal_value(element.attrib.get("风险费单价")),
        decimal_value(element.attrib.get("总价措施单价")),
        decimal_value(element.attrib.get("规费单价")),
        decimal_value(element.attrib.get("费用单价")),
        decimal_value(element.attrib.get("税金单价")),
        decimal_value(element.attrib.get("人工费合价")),
        decimal_value(element.attrib.get("材料费合价")),
        decimal_value(element.attrib.get("机械费合价")),
        decimal_value(element.attrib.get("管理费合价")),
        decimal_value(element.attrib.get("利润合价")),
        decimal_value(element.attrib.get("风险费合价")),
        decimal_value(element.attrib.get("总价措施合价")),
        decimal_value(element.attrib.get("规费合价")),
        decimal_value(element.attrib.get("费用合价")),
        decimal_value(element.attrib.get("税金合价")),
        text_value(element.attrib.get("专业类型"), 32) or "",
        decimal_value(element.attrib.get("未计价材料合价")),
        text_value(element.attrib.get("人工单价")) or "",
        decimal_value(element.attrib.get("暂估合价")),
        None,
        text_value(element.attrib.get("备注"), 500),
    )


def build_quota_row(boq_item_id: int, element: ET.Element) -> tuple[Any, ...]:
    return (
        boq_item_id,
        text_value(element.attrib.get("定额编号"), 64) or "",
        text_value(element.attrib.get("定额名称"), 255) or "",
        text_value(element.attrib.get("定额单位"), 32) or "",
        decimal_value(element.attrib.get("数量")),
        decimal_value(element.attrib.get("人工费单价")),
        decimal_value(element.attrib.get("材料费单价")),
        decimal_value(element.attrib.get("机械费单价")),
        decimal_value(element.attrib.get("管理费单价")),
        decimal_value(element.attrib.get("利润单价")),
        decimal_value(element.attrib.get("风险费单价")),
        decimal_value(element.attrib.get("总价措施单价")),
        decimal_value(element.attrib.get("规费单价")),
        decimal_value(element.attrib.get("费用单价")),
        decimal_value(element.attrib.get("税金单价")),
        decimal_value(element.attrib.get("综合单价")),
        decimal_value(element.attrib.get("综合合价")),
        decimal_value(element.attrib.get("人工费合价")),
        decimal_value(element.attrib.get("材料费合价")),
        decimal_value(element.attrib.get("机械费合价")),
        decimal_value(element.attrib.get("管理费合价")),
        decimal_value(element.attrib.get("利润合价")),
        decimal_value(element.attrib.get("风险费合价")),
        decimal_value(element.attrib.get("总价措施合价")),
        decimal_value(element.attrib.get("规费合价")),
        decimal_value(element.attrib.get("费用合价")),
        decimal_value(element.attrib.get("税金合价")),
        decimal_value(element.attrib.get("未计价材料合价")),
        decimal_value(element.attrib.get("暂估单价")),
        decimal_value(element.attrib.get("暂估合价")),
        text_value(element.attrib.get("专业类型"), 32) or "",
        text_value(element.attrib.get("备注"), 500),
    )


def collect_resource_summaries(root: ET.Element, batch_id: int) -> tuple[list[str], list[tuple[Any, ...]]]:
    ordered_ids: list[str] = []
    rows: list[tuple[Any, ...]] = []
    seen: set[str] = set()
    for element in root.findall(".//工料机汇总表"):
        resource_id = text_value(element.attrib.get("工料机ID"), 64)
        if not resource_id or resource_id in seen:
            continue
        seen.add(resource_id)
        ordered_ids.append(resource_id)
        rows.append(
            (
                batch_id,
                map_resource_type(element.attrib.get("材料类别")),
                text_value(element.attrib.get("材料编码"), 64),
                text_value(element.attrib.get("名称"), 255) or "",
                text_value(element.attrib.get("单位"), 32),
                decimal_value(element.attrib.get("单价"), default=None),
                build_resource_remark(element.attrib),
            )
        )
    return ordered_ids, rows
