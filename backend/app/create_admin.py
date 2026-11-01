from getpass import getpass
from uuid import uuid4

import psycopg

from app.database import get_connection
from app.passwords import password_hasher


def main() -> None:
    username = input("Username: ").strip()
    if not username:
        raise SystemExit("Username must not be empty.")

    password = getpass("Password (at least 8 characters): ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match.")

    password_hash = password_hasher.hash(password)
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (%s, %s, %s)",
                (uuid4(), username, password_hash),
            )
    except psycopg.errors.UniqueViolation:
        raise SystemExit("That username already exists. No changes were made.") from None
    except psycopg.Error:
        raise SystemExit(
            "Could not create the administrator. Check the database connection "
            "settings and run make db-setup."
        ) from None

    print(f"Administrator '{username}' created.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("\nAdministrator creation cancelled.") from None
