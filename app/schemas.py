from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.models import Gender


class EmployeeForm(BaseModel):
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(min_length=1, max_length=80)
    middle_name: str | None = Field(default=None, max_length=80)
    birth_date: date
    gender: Gender
    phone: str = Field(min_length=3, max_length=32)

    @field_validator("last_name", "first_name", "middle_name", "phone", mode="before")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @field_validator("last_name", "first_name")
    @classmethod
    def required_text(cls, value: str | None) -> str:
        if not value:
            raise ValueError("Обязательное поле")
        return value

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_past(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("Дата рождения должна быть в прошлом")
        return value

