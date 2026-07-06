"""add employee normalized keys

Revision ID: 20260706_0002
Revises: 20260704_0001
Create Date: 2026-07-06
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


revision = "20260706_0002"
down_revision = "20260704_0001"
branch_labels = None
depends_on = None


employees_table = sa.table(
    "employees",
    sa.column("id", sa.Integer()),
    sa.column("last_name", sa.String(length=80)),
    sa.column("last_name_key", sa.String(length=80)),
    sa.column("first_name", sa.String(length=80)),
    sa.column("first_name_key", sa.String(length=80)),
    sa.column("middle_name", sa.String(length=80)),
    sa.column("middle_name_key", sa.String(length=80)),
    sa.column("full_name_key", sa.String(length=260)),
    sa.column("phone", sa.String(length=32)),
    sa.column("phone_key", sa.String(length=15)),
)


def normalize_name_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def normalize_phone_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_existing_phone(value: str | None) -> str:
    digits = normalize_phone_digits(value)
    if not digits:
        return (value or "")[:16]
    return f"+{digits[:15]}"


def employee_name_key(last_name: str, first_name: str, middle_name: str | None) -> str:
    return normalize_name_text(" ".join(part for part in (last_name, first_name, middle_name) if part))


def backfill_employee_keys() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            employees_table.c.id,
            employees_table.c.last_name,
            employees_table.c.first_name,
            employees_table.c.middle_name,
            employees_table.c.phone,
        )
    )

    for row in rows.mappings():
        normalized_phone = normalize_existing_phone(row["phone"])
        connection.execute(
            employees_table.update()
            .where(employees_table.c.id == row["id"])
            .values(
                last_name_key=normalize_name_text(row["last_name"]),
                first_name_key=normalize_name_text(row["first_name"]),
                middle_name_key=normalize_name_text(row["middle_name"]),
                full_name_key=employee_name_key(row["last_name"], row["first_name"], row["middle_name"]),
                phone=normalized_phone,
                phone_key=normalize_phone_digits(normalized_phone),
            )
        )


def upgrade() -> None:
    op.add_column("employees", sa.Column("last_name_key", sa.String(length=80), nullable=True))
    op.add_column("employees", sa.Column("first_name_key", sa.String(length=80), nullable=True))
    op.add_column("employees", sa.Column("middle_name_key", sa.String(length=80), nullable=True))
    op.add_column("employees", sa.Column("full_name_key", sa.String(length=260), nullable=True))
    op.add_column("employees", sa.Column("phone_key", sa.String(length=15), nullable=True))

    backfill_employee_keys()

    op.drop_index(op.f("ix_employees_phone"), table_name="employees")
    with op.batch_alter_table("employees") as batch_op:
        batch_op.alter_column("last_name_key", existing_type=sa.String(length=80), nullable=False)
        batch_op.alter_column("first_name_key", existing_type=sa.String(length=80), nullable=False)
        batch_op.alter_column("middle_name_key", existing_type=sa.String(length=80), nullable=False)
        batch_op.alter_column("full_name_key", existing_type=sa.String(length=260), nullable=False)
        batch_op.alter_column("phone", existing_type=sa.String(length=32), type_=sa.String(length=16), nullable=False)
        batch_op.alter_column("phone_key", existing_type=sa.String(length=15), nullable=False)
        batch_op.create_unique_constraint(
            "uq_employees_identity",
            ["last_name_key", "first_name_key", "middle_name_key", "birth_date", "gender", "phone_key"],
        )

    op.create_index(op.f("ix_employees_last_name_key"), "employees", ["last_name_key"], unique=False)
    op.create_index(op.f("ix_employees_first_name_key"), "employees", ["first_name_key"], unique=False)
    op.create_index(op.f("ix_employees_full_name_key"), "employees", ["full_name_key"], unique=False)
    op.create_index(op.f("ix_employees_phone_key"), "employees", ["phone_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_employees_phone_key"), table_name="employees")
    op.drop_index(op.f("ix_employees_full_name_key"), table_name="employees")
    op.drop_index(op.f("ix_employees_first_name_key"), table_name="employees")
    op.drop_index(op.f("ix_employees_last_name_key"), table_name="employees")

    with op.batch_alter_table("employees") as batch_op:
        batch_op.drop_constraint("uq_employees_identity", type_="unique")
        batch_op.alter_column("phone", existing_type=sa.String(length=16), type_=sa.String(length=32), nullable=False)
        batch_op.drop_column("phone_key")
        batch_op.drop_column("full_name_key")
        batch_op.drop_column("middle_name_key")
        batch_op.drop_column("first_name_key")
        batch_op.drop_column("last_name_key")

    op.create_index(op.f("ix_employees_phone"), "employees", ["phone"], unique=False)
