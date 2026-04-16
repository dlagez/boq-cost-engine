from __future__ import annotations

from typing import Any


def _chunked(values: list[int], size: int = 500) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _select_ids(cursor: Any, sql: str, params: tuple[Any, ...]) -> list[int]:
    cursor.execute(sql, params)
    return [int(row["id"]) for row in cursor.fetchall()]


def _delete_by_ids(cursor: Any, table: str, column: str, ids: list[int]) -> None:
    if not ids:
        return
    for group in _chunked(ids):
        placeholders = ", ".join(["%s"] * len(group))
        cursor.execute(
            f"DELETE FROM {table} WHERE {column} IN ({placeholders})",
            tuple(group),
        )


def delete_batch_by_no(cursor: Any, batch_no: str) -> bool:
    cursor.execute(
        "SELECT id FROM cost_import_batch WHERE batch_no = %s",
        (batch_no,),
    )
    row = cursor.fetchone()
    if not row:
        return False

    batch_id = int(row["id"])
    single_project_ids = _select_ids(
        cursor,
        "SELECT id FROM cost_single_project WHERE batch_id = %s",
        (batch_id,),
    )
    _delete_by_ids(cursor, "cost_single_project_profile", "single_project_id", single_project_ids)
    _delete_by_ids(cursor, "cost_single_project_extra", "single_project_id", single_project_ids)

    unit_project_ids: list[int] = []
    if single_project_ids:
        for group in _chunked(single_project_ids):
            placeholders = ", ".join(["%s"] * len(group))
            unit_project_ids.extend(
                _select_ids(
                    cursor,
                    f"SELECT id FROM cost_unit_project WHERE single_project_id IN ({placeholders})",
                    tuple(group),
                )
            )

    _delete_by_ids(cursor, "cost_unit_project_extra", "unit_project_id", unit_project_ids)

    division_ids: list[int] = []
    if unit_project_ids:
        for group in _chunked(unit_project_ids):
            placeholders = ", ".join(["%s"] * len(group))
            division_ids.extend(
                _select_ids(
                    cursor,
                    f"SELECT id FROM cost_division WHERE unit_project_id IN ({placeholders})",
                    tuple(group),
                )
            )

    boq_item_ids: list[int] = []
    if division_ids:
        for group in _chunked(division_ids):
            placeholders = ", ".join(["%s"] * len(group))
            boq_item_ids.extend(
                _select_ids(
                    cursor,
                    f"SELECT id FROM cost_boq_item WHERE division_id IN ({placeholders})",
                    tuple(group),
                )
            )

    quota_ids: list[int] = []
    if boq_item_ids:
        for group in _chunked(boq_item_ids):
            placeholders = ", ".join(["%s"] * len(group))
            quota_ids.extend(
                _select_ids(
                    cursor,
                    f"SELECT id FROM cost_boq_item_quota WHERE boq_item_id IN ({placeholders})",
                    tuple(group),
                )
            )

    _delete_by_ids(cursor, "cost_quota_resource_usage", "quota_id", quota_ids)
    _delete_by_ids(cursor, "cost_boq_item_quota", "id", quota_ids)
    _delete_by_ids(cursor, "cost_boq_item", "id", boq_item_ids)
    _delete_by_ids(cursor, "cost_division", "id", division_ids)
    _delete_by_ids(cursor, "cost_unit_project", "id", unit_project_ids)
    cursor.execute("DELETE FROM cost_resource_summary WHERE batch_id = %s", (batch_id,))
    cursor.execute("DELETE FROM cost_single_project WHERE batch_id = %s", (batch_id,))
    cursor.execute("DELETE FROM cost_import_batch WHERE id = %s", (batch_id,))
    return True
