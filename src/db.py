from __future__ import annotations

import pymysql
from pymysql.connections import Connection

from config import get_mysql_config


def create_connection() -> Connection:
    config = get_mysql_config()
    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
