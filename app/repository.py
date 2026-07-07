from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Employee, Gender
from app.normalization import employee_name_key, normalize_name_text, normalize_phone_digits
from app.schemas import EmployeeForm


class DuplicateEmployeeError(ValueError):
    pass


def calculate_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def date_years_ago(today: date, years: int) -> date:
    """Return the date this many full years before today, clamping leap day to Feb 28."""
    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


def employee_key_values(data: EmployeeForm) -> dict[str, str]:
    """Build denormalized keys used consistently for search and duplicate constraints."""
    return {
        "last_name_key": normalize_name_text(data.last_name),
        "first_name_key": normalize_name_text(data.first_name),
        "middle_name_key": normalize_name_text(data.middle_name),
        "full_name_key": employee_name_key(data.last_name, data.first_name, data.middle_name),
        "phone_key": normalize_phone_digits(data.phone),
    }


def employee_filter_statement(
    query: str | None = None,
    gender: Gender | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
) -> Select[tuple[Employee]]:
    """Build the SQL predicate for registry filters without loading all employees."""
    stmt: Select[tuple[Employee]] = select(Employee)

    if gender:
        stmt = stmt.where(Employee.gender == gender)

    today = date.today()
    if age_min is not None:
        stmt = stmt.where(Employee.birth_date <= date_years_ago(today, age_min))
    if age_max is not None:
        # Age <= N means birth date is after the date when the employee would turn N + 1.
        stmt = stmt.where(Employee.birth_date > date_years_ago(today, age_max + 1))

    normalized_query = normalize_name_text(query)
    for token in normalized_query.split():
        token_digits = normalize_phone_digits(token)
        token_conditions = [Employee.full_name_key.contains(token, autoescape=True)]
        if token_digits:
            token_conditions.append(Employee.phone_key.contains(token_digits))
        stmt = stmt.where(or_(*token_conditions))

    return stmt


def count_employees(
    db: Session,
    query: str | None = None,
    gender: Gender | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
) -> int:
    filtered_stmt = employee_filter_statement(query=query, gender=gender, age_min=age_min, age_max=age_max)
    count_stmt = select(func.count()).select_from(filtered_stmt.subquery())
    return db.scalar(count_stmt) or 0


def list_employees(
    db: Session,
    query: str | None = None,
    gender: Gender | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Employee]:
    stmt = employee_filter_statement(query=query, gender=gender, age_min=age_min, age_max=age_max)
    stmt = stmt.order_by(Employee.last_name_key, Employee.first_name_key, Employee.id)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def find_duplicate_employee(db: Session, data: EmployeeForm, exclude_employee_id: int | None = None) -> Employee | None:
    key_values = employee_key_values(data)
    stmt = select(Employee).where(
        Employee.last_name_key == key_values["last_name_key"],
        Employee.first_name_key == key_values["first_name_key"],
        Employee.middle_name_key == key_values["middle_name_key"],
        Employee.birth_date == data.birth_date,
        Employee.gender == data.gender,
        Employee.phone_key == key_values["phone_key"],
    )
    if exclude_employee_id is not None:
        stmt = stmt.where(Employee.id != exclude_employee_id)
    return db.scalars(stmt).first()


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def commit_or_raise_duplicate(db: Session) -> None:
    """Commit a unit of work and expose unique-constraint conflicts as a domain error."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEmployeeError from exc


def create_employee(db: Session, data: EmployeeForm, photo_path: str | None = None) -> Employee:
    employee = Employee(**data.model_dump(), **employee_key_values(data), photo_path=photo_path)
    db.add(employee)
    commit_or_raise_duplicate(db)
    db.refresh(employee)
    return employee


def update_employee(db: Session, employee: Employee, data: EmployeeForm, photo_path: str | None = None) -> Employee:
    for field, value in (data.model_dump() | employee_key_values(data)).items():
        setattr(employee, field, value)
    if photo_path is not None:
        employee.photo_path = photo_path
    commit_or_raise_duplicate(db)
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee: Employee) -> None:
    db.delete(employee)
    db.commit()
