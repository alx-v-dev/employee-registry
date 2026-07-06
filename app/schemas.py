from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.models import Gender
from app.normalization import normalize_phone_e164


class EmployeeForm(BaseModel):
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(min_length=1, max_length=80)
    middle_name: str | None = Field(default=None, max_length=80)
    birth_date: date
    gender: Gender
    phone: str

    @field_validator("last_name", "first_name", "middle_name", "phone", mode="before")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("last_name", "first_name", "middle_name")
    @classmethod
    def format_name(cls, value: str | None) -> str | None:
        if not value:
            return value
        return "-".join(part[:1].upper() + part[1:].lower() for part in value.split("-"))

    @field_validator("last_name", "first_name")
    @classmethod
    def required_text(cls, value: str | None) -> str:
        if not value:
            raise ValueError("Обязательное поле")
        return value

    @field_validator("phone")
    @classmethod
    def phone_must_be_e164(cls, value: str | None) -> str:
        if not value:
            raise ValueError("Обязательное поле")
        try:
            return normalize_phone_e164(value)
        except ValueError as exc:
            raise ValueError("Телефон должен быть в формате E.164, например +12025550123") from exc

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_past(cls, value: date) -> date:
        if value.year < 1000:
            raise ValueError("Год рождения должен быть указан четырьмя цифрами")
        if value >= date.today():
            raise ValueError("Дата рождения должна быть в прошлом")
        return value
