from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

from pymysql import MySQLError

from db import create_connection
from xml_importer_lib import import_xml_file


def main() -> None:
    if len(sys.argv) > 1:
        batch_no, stats = import_xml_file(Path(sys.argv[1]))
        print(f"Imported batch: {batch_no}")
        print(
            "single_projects={single_projects}, profiles={single_project_profiles}, "
            "unit_projects={unit_projects}, unit_extras={unit_project_extras}, "
            "divisions={divisions}, boq_items={boq_items}, quotas={quotas}, "
            "resource_summaries={resource_summaries}, resource_usages={resource_usages}, "
            "elapsed_seconds={elapsed_seconds:.2f}".format(
                **asdict(stats)
            )
        )
        return

    print("Starting application...")

    try:
        connection = create_connection()
    except MySQLError as exc:
        print(f"MySQL connection failed: {exc}")
        return

    with connection:
        print("MySQL connection succeeded.")


if __name__ == "__main__":
    main()
