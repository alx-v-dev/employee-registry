from pathlib import Path

from alembic import command
from alembic.config import Config
import sqlalchemy as sa

from app.config import get_settings


def create_legacy_employee_schema(connection: sa.Connection) -> None:
    """Create the pre-normalization schema used by local databases before Alembic 0002."""
    connection.execute(
        sa.text(
            """
            CREATE TABLE employees (
                id INTEGER NOT NULL,
                last_name VARCHAR(80) NOT NULL,
                first_name VARCHAR(80) NOT NULL,
                middle_name VARCHAR(80),
                birth_date DATE NOT NULL,
                gender VARCHAR(6) NOT NULL,
                phone VARCHAR(32) NOT NULL,
                photo_path VARCHAR(255),
                PRIMARY KEY (id)
            )
            """
        )
    )
    connection.execute(sa.text("CREATE INDEX ix_employees_id ON employees (id)"))
    connection.execute(sa.text("CREATE INDEX ix_employees_last_name ON employees (last_name)"))
    connection.execute(sa.text("CREATE INDEX ix_employees_first_name ON employees (first_name)"))
    connection.execute(sa.text("CREATE INDEX ix_employees_gender ON employees (gender)"))
    connection.execute(sa.text("CREATE INDEX ix_employees_phone ON employees (phone)"))


def test_migrations_upgrade_legacy_employee_schema(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "legacy.db"
    database_url = f"sqlite:///{database_path}"
    engine = sa.create_engine(database_url)

    with engine.begin() as connection:
        create_legacy_employee_schema(connection)
        connection.execute(
            sa.text(
                """
                INSERT INTO employees (
                    last_name, first_name, middle_name, birth_date, gender, phone, photo_path
                ) VALUES (
                    'Ivanov', 'Ivan', 'Ivanovich', '1990-01-01', 'male', '+7 (999) 000-00-00', NULL
                )
                """
            )
        )

    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        alembic_config = Config("alembic.ini")
        # Legacy local databases match the first migration but do not have an Alembic version row.
        command.stamp(alembic_config, "20260704_0001")
        command.upgrade(alembic_config, "head")
    finally:
        get_settings.cache_clear()

    with engine.connect() as connection:
        columns = {row[1] for row in connection.execute(sa.text("PRAGMA table_info(employees)"))}
        assert {"last_name_key", "first_name_key", "middle_name_key", "full_name_key", "phone_key"} <= columns

        row = connection.execute(
            sa.text(
                """
                SELECT last_name_key, first_name_key, middle_name_key, full_name_key, phone, phone_key
                FROM employees
                """
            )
        ).one()
        assert row == ("ivanov", "ivan", "ivanovich", "ivanov ivan ivanovich", "+79990000000", "79990000000")
