from collections.abc import Generator
from pathlib import Path
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    settings = get_settings()
    original_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path / "uploads"

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    settings.upload_dir = original_upload_dir


def employee_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "last_name": "Ivanov",
        "first_name": "Ivan",
        "middle_name": "Ivanovich",
        "birth_date": "1990-01-01",
        "gender": "male",
        "phone": "+7 (999) 000-00-00",
    }
    payload.update(overrides)
    return payload


def test_registry_empty_state(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Сотрудники не найдены" in response.text


def test_create_filter_update_and_delete_employee(client: TestClient) -> None:
    response = client.post("/employees", data=employee_payload(), follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    response = client.get("/?q=Ivanov&gender=male&age_min=30&age_max=50")
    assert response.status_code == 200
    assert "Ivanov Ivan Ivanovich" in response.text
    assert "+7 (999) 000-00-00" in response.text
    assert response.headers["content-type"].startswith("text/html")

    employee_id = re.search(r"/employees/(\d+)/edit", response.text).group(1)
    response = client.post(
        f"/employees/{employee_id}",
        data=employee_payload(first_name="Petr", phone="+70000000000"),
        follow_redirects=False,
    )
    assert response.status_code == 303

    response = client.get("/?q=Petr")
    assert "Ivanov Petr Ivanovich" in response.text
    assert "+70000000000" in response.text

    response = client.post(f"/employees/{employee_id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/?q=Petr").text.count("Ivanov Petr Ivanovich") == 0


def test_smart_search_by_name_tokens_and_phone_digits(client: TestClient) -> None:
    client.post("/employees", data=employee_payload())
    client.post(
        "/employees",
        data=employee_payload(
            last_name="Petrov",
            first_name="Petr",
            middle_name="Petrovich",
            phone="+7 (111) 222-33-44",
        ),
    )

    response = client.get("/?q=Ivanov")
    assert response.status_code == 200
    assert "Ivanov Ivan Ivanovich" in response.text
    assert "Petrov Petr Petrovich" not in response.text

    response = client.get("/?q=Ivanov+Ivan")
    assert "Ivanov Ivan Ivanovich" in response.text

    response = client.get("/?q=Ivan+Ivanov")
    assert "Ivanov Ivan Ivanovich" in response.text

    response = client.get("/?q=79990000000")
    assert "Ivanov Ivan Ivanovich" in response.text

    response = client.get("/?q=999000")
    assert "Ivanov Ivan Ivanovich" in response.text

    response = client.get("/?q=Ivanov&gender=male&age_min=30&age_max=50")
    assert response.headers["content-type"].startswith("text/html")
    assert "Ivanov Ivan Ivanovich" in response.text


def test_search_with_empty_filter_values_returns_registry_page(client: TestClient) -> None:
    client.post("/employees", data=employee_payload())

    response = client.get("/?q=Ivanov&gender=&age_min=&age_max=&page=")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Ivanov Ivan Ivanovich" in response.text
    assert '"detail"' not in response.text


def test_search_with_invalid_query_params_still_returns_registry_page(client: TestClient) -> None:
    client.post("/employees", data=employee_payload())

    response = client.get("/?q=Ivanov&gender=unknown&age_min=abc&age_max=-5&page=bad")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Ivanov Ivan Ivanovich" in response.text
    assert '"detail"' not in response.text


def test_photo_size_limit(client: TestClient) -> None:
    files = {"photo": ("large.png", b"x" * (200 * 1024 + 1), "image/png")}
    response = client.post("/employees", data=employee_payload(), files=files)

    assert response.status_code == 422
    assert "Размер фото не должен превышать 200 КБ" in response.text


def test_registry_pagination(client: TestClient) -> None:
    for index in range(7):
        client.post(
            "/employees",
            data=employee_payload(last_name=f"User{index:02d}", first_name="Test", phone=f"+700000000{index:02d}"),
        )

    response = client.get("/")
    assert response.status_code == 200
    assert "?page=2" in response.text
    assert "User06 Test Ivanovich" not in response.text

    response = client.get("/?page=2")
    assert response.status_code == 200
    assert "User06 Test Ivanovich" in response.text


def test_search_pagination_uses_filtered_results(client: TestClient) -> None:
    for index in range(7):
        client.post(
            "/employees",
            data=employee_payload(last_name=f"SearchUser{index:02d}", first_name="Test", phone=f"+711100000{index:02d}"),
        )
    client.post("/employees", data=employee_payload(last_name="OtherUser", first_name="Test", phone="+72220000000"))

    response = client.get("/?q=SearchUser")
    assert response.status_code == 200
    assert "/?q=SearchUser&amp;page=2" in response.text
    assert "Searchuser06 Test Ivanovich" not in response.text
    assert "OtherUser Test Ivanovich" not in response.text

    response = client.get("/?q=SearchUser&page=2")
    assert response.status_code == 200
    assert "Searchuser06 Test Ivanovich" in response.text
    assert "OtherUser Test Ivanovich" not in response.text


def test_invalid_birth_dates_are_rejected(client: TestClient) -> None:
    assert client.post("/employees", data=employee_payload(birth_date="9999-01-01")).status_code == 422
    assert client.post("/employees", data=employee_payload(birth_date="0999-01-01")).status_code == 422
    assert client.post("/employees", data=employee_payload(birth_date="2020-13-01")).status_code == 422
    assert client.post("/employees", data=employee_payload(birth_date="2021-02-29")).status_code == 422


def test_duplicate_employee_is_rejected_without_losing_input(client: TestClient) -> None:
    response = client.post("/employees", data=employee_payload(last_name="ivanov", first_name="ivan"), follow_redirects=False)
    assert response.status_code == 303

    response = client.post("/employees", data=employee_payload(last_name="ivanov", first_name="ivan"))
    assert response.status_code == 422
    assert "Сотрудник с такими данными уже существует" in response.text
    assert "Ivanov" in response.text
    assert "Продолжить ввод данных" in response.text
    assert "Вернуться на главную" in response.text
