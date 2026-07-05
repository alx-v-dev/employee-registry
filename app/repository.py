from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models import Employee, Gender
from app.schemas import EmployeeForm


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

    if query:
        like_query = f"%{query.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Employee.last_name).like(like_query),
                func.lower(Employee.first_name).like(like_query),
                func.lower(Employee.middle_name).like(like_query),
                func.lower(Employee.phone).like(like_query),
            )
        )
    if gender:
        stmt = stmt.where(Employee.gender == gender)

    employees = list(db.scalars(stmt))
    if age_min is not None:
        employees = [employee for employee in employees if calculate_age(employee.birth_date) >= age_min]
    if age_max is not None:
        employees = [employee for employee in employees if calculate_age(employee.birth_date) <= age_max]
    return employees


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

