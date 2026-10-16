from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterator


def database_path() -> Path:
    return Path(os.getenv("STUDENT_DB_PATH", "data/students.db")).expanduser()


def connect() -> sqlite3.Connection:
    path = database_path()
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                course TEXT,
                address TEXT,
                enrollment_date TEXT,
                CHECK (email IS NOT NULL OR phone IS NOT NULL)
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_students_name ON students(name)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_students_course ON students(course)")


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
