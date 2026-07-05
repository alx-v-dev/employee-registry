from typing import Annotated
from datetime import date, timedelta
from math import ceil
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, Gender
from app.photos import PhotoValidationError, delete_photo, save_photo
from app.repository import create_employee, delete_employee, find_duplicate_employee, get_employee, list_employees, update_employee
from app.schemas import EmployeeForm


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
PAGE_SIZE = 6
MIN_BIRTH_DATE = "1000-01-01"


def redirect_to_registry() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


def max_birth_date() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def form_context(
    employee: Employee | None,
    values: dict[str, str],
    errors: list[dict[str, object]],
    title: str,
    duplicate_warning: bool = False,
) -> dict[str, object]:
    return {
        "employee": employee,
        "values": values,
        "errors": errors,
        "title": title,
        "min_birth_date": MIN_BIRTH_DATE,
        "max_birth_date": max_birth_date(),
        "max_photo_size": 200 * 1024,
        "duplicate_warning": duplicate_warning,
    }


def page_url(page: int, filters: dict[str, object]) -> str:
    params = {key: value for key, value in filters.items() if value not in ("", None)}
    params["page"] = page
    return f"/?{urlencode(params)}"


def parse_gender(value: str | None) -> Gender | None:
    if not value:
        return None
    try:
        return Gender(value)
    except ValueError:
        return None


def parse_non_negative_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def parse_page(value: str | None) -> int:
    if not value:
        return 1
    try:
        parsed = int(value)
    except ValueError:
        return 1
    return parsed if parsed > 0 else 1


def build_employee_form(
    last_name: Annotated[str, Form()],
    first_name: Annotated[str, Form()],
    middle_name: Annotated[str | None, Form()] = None,
    birth_date: Annotated[str, Form()] = "",
    gender: Annotated[Gender, Form()] = Gender.male,
    phone: Annotated[str, Form()] = "",
) -> EmployeeForm:
    return EmployeeForm(
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        birth_date=birth_date,
        gender=gender,
        phone=phone,
    )


def form_values(employee: Employee | None = None, form: EmployeeForm | None = None) -> dict[str, str]:
    if form:
        values = form.model_dump()
    elif employee:
        values = {
            "last_name": employee.last_name,
            "first_name": employee.first_name,
            "middle_name": employee.middle_name or "",
            "birth_date": employee.birth_date,
            "gender": employee.gender,
            "phone": employee.phone,
        }
    else:
        values = {"last_name": "", "first_name": "", "middle_name": "", "birth_date": "", "gender": Gender.male, "phone": ""}

    values["birth_date"] = values["birth_date"].isoformat() if values["birth_date"] else ""
    values["gender"] = values["gender"].value if isinstance(values["gender"], Gender) else values["gender"]
    return values


def submitted_values(
    last_name: str,
    first_name: str,
    middle_name: str | None,
    birth_date: str,
    gender: Gender | str,
    phone: str,
) -> dict[str, str]:
    gender_value = gender.value if isinstance(gender, Gender) else gender
    return {
        "last_name": last_name,
        "first_name": first_name,
        "middle_name": middle_name or "",
        "birth_date": birth_date,
        "gender": gender_value,
        "phone": phone,
    }


@router.get("/")
def registry(
    request: Request,
    q: str | None = None,
    gender: str | None = None,
    age_min: str | None = None,
    age_max: str | None = None,
    page: str | None = None,
    db: Session = Depends(get_db),
):
    parsed_gender = parse_gender(gender)
    parsed_age_min = parse_non_negative_int(age_min)
    parsed_age_max = parse_non_negative_int(age_max)
    parsed_page = parse_page(page)

    employees = list_employees(db, query=q, gender=parsed_gender, age_min=parsed_age_min, age_max=parsed_age_max)
    total_count = len(employees)
    total_pages = max(1, ceil(total_count / PAGE_SIZE))
    current_page = min(parsed_page, total_pages)
    start = (current_page - 1) * PAGE_SIZE
    filters = {
        "q": q or "",
        "gender": parsed_gender.value if parsed_gender else "",
        "age_min": parsed_age_min if parsed_age_min is not None else "",
        "age_max": parsed_age_max if parsed_age_max is not None else "",
    }
    page_links = [{"number": number, "url": page_url(number, filters), "active": number == current_page} for number in range(1, total_pages + 1)]

    return templates.TemplateResponse(
        request,
        "registry.html",
        {
            "employees": employees[start : start + PAGE_SIZE],
            "filters": filters,
            "pagination": {
                "page": current_page,
                "total_pages": total_pages,
                "total_count": total_count,
                "previous_url": page_url(current_page - 1, filters) if current_page > 1 else "",
                "next_url": page_url(current_page + 1, filters) if current_page < total_pages else "",
                "page_links": page_links,
            },
        },
    )


@router.get("/employees/new")
def new_employee(request: Request):
    return templates.TemplateResponse(
        request,
        "employee_form.html",
        form_context(None, form_values(), [], "Новый сотрудник"),
    )


def validation_response(
    request: Request,
    employee: Employee | None,
    values: dict[str, str],
    errors: list[dict[str, object]],
    title: str,
    duplicate_warning: bool = False,
):
    return templates.TemplateResponse(
        request,
        "employee_form.html",
        form_context(employee, values, errors, title, duplicate_warning=duplicate_warning),
        status_code=422,
    )


@router.post("/employees")
async def create_employee_route(
    request: Request,
    db: Session = Depends(get_db),
    last_name: Annotated[str, Form()] = "",
    first_name: Annotated[str, Form()] = "",
    middle_name: Annotated[str | None, Form()] = None,
    birth_date: Annotated[str, Form()] = "",
    gender: Annotated[Gender, Form()] = Gender.male,
    phone: Annotated[str, Form()] = "",
    photo: UploadFile | None = File(default=None),
):
    values = submitted_values(last_name, first_name, middle_name, birth_date, gender, phone)
    try:
        form = build_employee_form(last_name, first_name, middle_name, birth_date, gender, phone)
    except ValidationError as exc:
        return validation_response(request, None, values, exc.errors(), "Новый сотрудник")

    if find_duplicate_employee(db, form):
        return validation_response(
            request,
            None,
            form_values(form=form),
            [{"msg": "Сотрудник с такими данными уже существует"}],
            "Новый сотрудник",
            duplicate_warning=True,
        )

    try:
        photo_path = await save_photo(photo)
    except PhotoValidationError as exc:
        return validation_response(request, None, values, [{"msg": str(exc)}], "Новый сотрудник")

    create_employee(db, form, photo_path=photo_path)
    return redirect_to_registry()


@router.get("/employees/{employee_id}/edit")
def edit_employee(employee_id: int, request: Request, db: Session = Depends(get_db)):
    employee = get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request,
        "employee_form.html",
        form_context(employee, form_values(employee), [], "Редактирование"),
    )


@router.post("/employees/{employee_id}")
async def update_employee_route(
    employee_id: int,
    request: Request,
    db: Session = Depends(get_db),
    last_name: Annotated[str, Form()] = "",
    first_name: Annotated[str, Form()] = "",
    middle_name: Annotated[str | None, Form()] = None,
    birth_date: Annotated[str, Form()] = "",
    gender: Annotated[Gender, Form()] = Gender.male,
    phone: Annotated[str, Form()] = "",
    photo: UploadFile | None = File(default=None),
):
    employee = get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    values = submitted_values(last_name, first_name, middle_name, birth_date, gender, phone)
    try:
        form = build_employee_form(last_name, first_name, middle_name, birth_date, gender, phone)
    except ValidationError as exc:
        return validation_response(request, employee, values, exc.errors(), "Редактирование")

    if find_duplicate_employee(db, form, exclude_employee_id=employee.id):
        return validation_response(
            request,
            employee,
            form_values(form=form),
            [{"msg": "Сотрудник с такими данными уже существует"}],
            "Редактирование",
            duplicate_warning=True,
        )

    try:
        photo_path = await save_photo(photo, old_photo_path=employee.photo_path)
    except PhotoValidationError as exc:
        return validation_response(request, employee, values, [{"msg": str(exc)}], "Редактирование")

    update_employee(db, employee, form, photo_path=photo_path)
    return redirect_to_registry()


@router.post("/employees/{employee_id}/delete")
def delete_employee_route(employee_id: int, db: Session = Depends(get_db)):
    employee = get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    photo_path = employee.photo_path
    delete_employee(db, employee)
    delete_photo(photo_path)
    return redirect_to_registry()
