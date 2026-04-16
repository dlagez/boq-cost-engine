from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from db import create_connection

from .db_ops import executemany_insert, insert_row
from .helpers import ONE, build_batch_no, decimal_value, text_value
from .mappers import (
    build_batch_row,
    build_boq_item_row,
    build_division_row,
    build_quota_row,
    build_single_project_profiles,
    build_single_project_row,
    build_unit_project_extra_rows,
    build_unit_project_row,
    collect_resource_summaries,
)
from .models import ImportStats
from .sql import (
    INSERT_BOQ_ITEM_QUOTA_SQL,
    INSERT_BOQ_ITEM_SQL,
    INSERT_DIVISION_SQL,
    INSERT_IMPORT_BATCH_SQL,
    INSERT_RESOURCE_SUMMARY_SQL,
    INSERT_RESOURCE_USAGE_SQL,
    INSERT_SINGLE_PROJECT_PROFILE_SQL,
    INSERT_SINGLE_PROJECT_SQL,
    INSERT_UNIT_PROJECT_EXTRA_SQL,
    INSERT_UNIT_PROJECT_SQL,
)


def insert_resource_summaries(cursor: Any, root: ET.Element, batch_id: int) -> dict[str, int]:
    ordered_unique_ids, rows = collect_resource_summaries(root, batch_id)
    executemany_insert(cursor, INSERT_RESOURCE_SUMMARY_SQL, rows)

    resource_map: dict[str, int] = {}
    cursor.execute(
        "SELECT id FROM cost_resource_summary WHERE batch_id = %s ORDER BY id",
        (batch_id,),
    )
    inserted_rows = cursor.fetchall()

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
                batch_id = insert_row(cursor, INSERT_IMPORT_BATCH_SQL, build_batch_row(root, file_path, batch_no))
                resource_summary_map = insert_resource_summaries(cursor, root, batch_id)
                stats.resource_summaries = len(resource_summary_map)

                for single_project_element in root.findall("单项工程基本信息表"):
                    single_project_id = insert_row(
                        cursor,
                        INSERT_SINGLE_PROJECT_SQL,
                        build_single_project_row(batch_id, single_project_element),
                    )
                    stats.single_projects += 1

                    profile_rows = build_single_project_profiles(single_project_id, single_project_element)
                    executemany_insert(cursor, INSERT_SINGLE_PROJECT_PROFILE_SQL, profile_rows)
                    stats.single_project_profiles += len(profile_rows)

                    for unit_project_element in single_project_element.findall("单位工程基本信息表"):
                        unit_project_id = insert_row(
                            cursor,
                            INSERT_UNIT_PROJECT_SQL,
                            build_unit_project_row(single_project_id, unit_project_element),
                        )
                        stats.unit_projects += 1

                        unit_extra_rows = build_unit_project_extra_rows(unit_project_id, unit_project_element)
                        executemany_insert(cursor, INSERT_UNIT_PROJECT_EXTRA_SQL, unit_extra_rows)
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
                                INSERT_DIVISION_SQL,
                                build_division_row(unit_project_id, division_element, division_index),
                            )
                            stats.divisions += 1

                            for boq_item_element in division_element.findall("分部分项工程量清单与计价表"):
                                boq_item_id = insert_row(
                                    cursor,
                                    INSERT_BOQ_ITEM_SQL,
                                    build_boq_item_row(division_id, boq_item_element),
                                )
                                stats.boq_items += 1

                                for quota_element in boq_item_element.findall("分部分项工程量清单项目子目组价表"):
                                    quota_id = insert_row(
                                        cursor,
                                        INSERT_BOQ_ITEM_QUOTA_SQL,
                                        build_quota_row(boq_item_id, quota_element),
                                    )
                                    stats.quotas += 1

                                    usage_rows: list[tuple[Any, ...]] = []
                                    for usage_element in quota_element.findall("工料机含量表"):
                                        xml_resource_id = text_value(usage_element.attrib.get("汇总材料ID"), 64)
                                        if not xml_resource_id:
                                            continue
                                        resource_summary_id = resource_summary_map.get(xml_resource_id)
                                        if resource_summary_id is None:
                                            continue
                                        usage_rows.append(
                                            (
                                                quota_id,
                                                resource_summary_id,
                                                decimal_value(usage_element.attrib.get("消耗量定额含量")),
                                                decimal_value(
                                                    usage_element.attrib.get("消耗量定额含量调整系数"),
                                                    default=ONE,
                                                ),
                                            )
                                        )
                                    executemany_insert(cursor, INSERT_RESOURCE_USAGE_SQL, usage_rows)
                                    stats.resource_usages += len(usage_rows)

            connection.commit()
        except Exception:
            connection.rollback()
            raise

    return batch_no, stats
