from __future__ import annotations

from typing import Any


def insert_row(cursor: Any, sql: str, params: tuple[Any, ...]) -> int:
    cursor.execute(sql, params)
    return int(cursor.lastrowid)


def executemany_insert(cursor: Any, sql: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    cursor.executemany(sql, rows)
