from datetime import date
import re

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models import Employee, Gender
from app.schemas import EmployeeForm


def normalize_name_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def normalize_phone(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def employee_matches_query(employee: Employee, query: str | None) -> bool:
    normalized_query = normalize_name_text(query)
    if not normalized_query:
        return True

    full_name = normalize_name_text(employee.full_name)
    phone_digits = normalize_phone(employee.phone)

    for token in normalized_query.split():
        token_digits = normalize_phone(token)
        matches_name = token in full_name
        matches_phone = bool(token_digits) and token_digits in phone_digits
        if not matches_name and not matches_phone:
            return False
    return True


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def list_employees(
    db: Session,
    query: str | None = None,
    gender: Gender | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
) -> list[Employee]:
    stmt: Select[tuple[Employee]] = select(Employee).order_by(Employee.last_name, Employee.first_name)

    if gender:
        stmt = stmt.where(Employee.gender == gender)

    employees = list(db.scalars(stmt))
    employees = [employee for employee in employees if employee_matches_query(employee, query)]
    if age_min is not None:
        employees = [employee for employee in employees if calculate_age(employee.birth_date) >= age_min]
    if age_max is not None:
        employees = [employee for employee in employees if calculate_age(employee.birth_date) <= age_max]
    return employees


def find_duplicate_employee(db: Session, data: EmployeeForm, exclude_employee_id: int | None = None) -> Employee | None:
    stmt = select(Employee).where(
        and_(
            func.lower(Employee.last_name) == data.last_name.lower(),
            func.lower(Employee.first_name) == data.first_name.lower(),
            func.lower(func.coalesce(Employee.middle_name, "")) == (data.middle_name or "").lower(),
            Employee.birth_date == data.birth_date,
            Employee.gender == data.gender,
            Employee.phone == data.phone,
        )
    )
    if exclude_employee_id is not None:
        stmt = stmt.where(Employee.id != exclude_employee_id)
    return db.scalars(stmt).first()


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def create_employee(db: Session, data: EmployeeForm, photo_path: str | None = None) -> Employee:
    employee = Employee(**data.model_dump(), photo_path=photo_path)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(db: Session, employee: Employee, data: EmployeeForm, photo_path: str | None = None) -> Employee:
    for field, value in data.model_dump().items():
        setattr(employee, field, value)
    if photo_path is not None:
        employee.photo_path = photo_path
    db.commit()
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee: Employee) -> None:
    db.delete(employee)
    db.commit()
