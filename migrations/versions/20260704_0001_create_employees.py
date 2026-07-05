"""create employees

Revision ID: 20260704_0001
Revises:
Create Date: 2026-07-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260704_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("middle_name", sa.String(length=80), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("gender", sa.Enum("male", "female", name="gender"), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("photo_path", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employees_id"), "employees", ["id"], unique=False)
    op.create_index(op.f("ix_employees_last_name"), "employees", ["last_name"], unique=False)
    op.create_index(op.f("ix_employees_first_name"), "employees", ["first_name"], unique=False)
    op.create_index(op.f("ix_employees_gender"), "employees", ["gender"], unique=False)
    op.create_index(op.f("ix_employees_phone"), "employees", ["phone"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_employees_phone"), table_name="employees")
    op.drop_index(op.f("ix_employees_gender"), table_name="employees")
    op.drop_index(op.f("ix_employees_first_name"), table_name="employees")
    op.drop_index(op.f("ix_employees_last_name"), table_name="employees")
    op.drop_index(op.f("ix_employees_id"), table_name="employees")
    op.drop_table("employees")

