from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, Gender
from app.photos import PhotoValidationError, delete_photo, save_photo
from app.repository import create_employee, delete_employee, get_employee, list_employees, update_employee
from app.schemas import EmployeeForm


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def redirect_to_registry() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


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
    gender: Gender | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    db: Session = Depends(get_db),
):
    employees = list_employees(db, query=q, gender=gender, age_min=age_min, age_max=age_max)
    return templates.TemplateResponse(
        request,
        "registry.html",
        {
            "employees": employees,
            "filters": {"q": q or "", "gender": gender.value if gender else "", "age_min": age_min or "", "age_max": age_max or ""},
        },
    )


@router.get("/employees/new")
def new_employee(request: Request):
    return templates.TemplateResponse(
        request,
        "employee_form.html",
        {"employee": None, "values": form_values(), "errors": [], "title": "Новый сотрудник"},
    )


def validation_response(
    request: Request,
    employee: Employee | None,
    values: dict[str, str],
    errors: list[dict[str, object]],
    title: str,
):
    return templates.TemplateResponse(
        request,
        "employee_form.html",
        {"employee": employee, "values": values, "errors": errors, "title": title},
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
        {"employee": employee, "values": form_values(employee), "errors": [], "title": "Редактирование"},
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
