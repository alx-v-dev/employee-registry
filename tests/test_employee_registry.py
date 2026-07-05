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
        "phone": "+79990000000",
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
    assert "+79990000000" in response.text

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


def test_photo_size_limit(client: TestClient) -> None:
    files = {"photo": ("large.png", b"x" * (200 * 1024 + 1), "image/png")}
    response = client.post("/employees", data=employee_payload(), files=files)

    assert response.status_code == 422
    assert "Размер фото не должен превышать 200 КБ" in response.text
