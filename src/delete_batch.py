from __future__ import annotations

import argparse

from db import create_connection
from xml_importer_lib.batch_cleanup import delete_batch_by_no


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete imported data by batch number.")
    parser.add_argument("batch_no", help="Batch number to delete.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with create_connection() as connection:
        try:
            with connection.cursor() as cursor:
                deleted = delete_batch_by_no(cursor, args.batch_no)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    if deleted:
        print(f"Deleted batch: {args.batch_no}")
    else:
        print(f"Batch not found: {args.batch_no}")


if __name__ == "__main__":
    main()
