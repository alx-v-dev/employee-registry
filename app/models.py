import enum
from datetime import date

from sqlalchemy import Date, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Gender(str, enum.Enum):
    male = "male"
    female = "female"


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint(
            "last_name_key",
            "first_name_key",
            "middle_name_key",
            "birth_date",
            "gender",
            "phone_key",
            name="uq_employees_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    last_name_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    first_name_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    middle_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    middle_name_key: Mapped[str] = mapped_column(String(80), nullable=False)
    full_name_key: Mapped[str] = mapped_column(String(260), nullable=False, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    phone_key: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    @property
    def full_name(self) -> str:
        return " ".join(part for part in (self.last_name, self.first_name, self.middle_name) if part)
