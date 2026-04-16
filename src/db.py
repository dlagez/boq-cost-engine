from __future__ import annotations

import pymysql
from pymysql.connections import Connection

from config import get_mysql_config


def create_connection(*, include_database: bool = True) -> Connection:
    config = get_mysql_config()
    connection_kwargs = dict(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    if include_database:
        connection_kwargs["database"] = config.database
    return pymysql.connect(**connection_kwargs)
