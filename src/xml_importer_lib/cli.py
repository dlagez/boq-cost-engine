from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from .service import import_xml_file


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
