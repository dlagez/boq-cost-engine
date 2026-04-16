from __future__ import annotations

from db import create_connection

TABLES = (
    "cost_quota_resource_usage",
    "cost_boq_item_quota",
    "cost_boq_item",
    "cost_division",
    "cost_unit_project_extra",
    "cost_unit_project",
    "cost_single_project_profile",
    "cost_single_project_extra",
    "cost_resource_summary",
    "cost_single_project",
    "cost_import_batch",
)


def main() -> None:
    with create_connection() as connection:
        try:
            with connection.cursor() as cursor:
                for table in TABLES:
                    cursor.execute(f"TRUNCATE TABLE {table}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    print(f"Cleared {len(TABLES)} tables.")


if __name__ == "__main__":
    main()
