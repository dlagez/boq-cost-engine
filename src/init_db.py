from __future__ import annotations

from pathlib import Path

from config import get_mysql_config
from db import create_connection


def load_statements(schema_path: Path) -> list[str]:
    content = schema_path.read_text(encoding="utf-8")
    return [statement.strip() for statement in content.split(";") if statement.strip()]


def main() -> None:
    config = get_mysql_config()
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "init_schema.sql"
    statements = load_statements(schema_path)

    with create_connection(include_database=False) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.database}` "
                "DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci"
            )
            cursor.execute(f"USE `{config.database}`")
            for statement in statements:
                cursor.execute(statement)
        connection.commit()

    print(f"Database `{config.database}` is ready.")
    print(f"Applied {len(statements)} schema statements from {schema_path.name}.")


if __name__ == "__main__":
    main()
