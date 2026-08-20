"""
db.py
Small helper module that manages MySQL connections using PyMySQL.
"""

import os
import pymysql
import pymysql.cursors


def get_connection():
    """
    Opens and returns a new MySQL connection.
    Using DictCursor so query results come back as dictionaries
    (e.g. {"id": 1, "title": "Buy milk"}) instead of plain tuples.
    """
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "todo_app"),
        port=int(os.getenv("DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
