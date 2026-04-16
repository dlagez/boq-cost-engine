from __future__ import annotations

from pymysql import MySQLError

from db import create_connection


def main() -> None:
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
