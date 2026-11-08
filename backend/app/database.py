import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def connection_options():
    return dict(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
        row_factory=dict_row,
    )


def get_connection() -> psycopg.Connection:
    return psycopg.connect(**connection_options())


async def get_stream_connection() -> psycopg.AsyncConnection:
    return await psycopg.AsyncConnection.connect(**connection_options(), autocommit=True)
