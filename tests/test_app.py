import random
from datetime import date

import pytest

from app import (PROGRAM_TEMPLATES, calculate_bmi, calculate_calories, create_app,
                 generate_program, membership_state)


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def ravi(client):
    client.post("/clients", json={"name": "Ravi", "age": 30, "height": 175, "weight": 70,
                                  "program": "FL", "membership_end": "2099-12-31"})
    return client


# ---------- business logic ----------
def test_calories_per_program():
    assert calculate_calories(70, "FL") == 1540
    assert calculate_calories(70, "MG") == 2450
    assert calculate_calories(70, "BG") == 1820


def test_calories_invalid():
    with pytest.raises(ValueError):
        calculate_calories(70, "XX")
    with pytest.raises(ValueError):
        calculate_calories(0, "FL")


@pytest.mark.parametrize("weight,height,category", [
    (50, 175, "Underweight"), (70, 175, "Normal"), (85, 175, "Overweight"), (100, 175, "Obese")])
def test_bmi_categories(weight, height, category):
    assert calculate_bmi(weight, height)["category"] == category


def test_bmi_value_and_invalid():
    assert calculate_bmi(70, 175)["bmi"] == 22.9
    with pytest.raises(ValueError):
        calculate_bmi(70, 0)


def test_membership_state():
    today = date(2026, 10, 1)
    assert membership_state("2026-12-31", today) == "Active"
    assert membership_state("2026-01-01", today) == "Expired"
    assert membership_state(None, today) == "Inactive"


def test_generate_program_uses_templates():
    program_type, detail = generate_program(random.Random(1))
    assert detail in PROGRAM_TEMPLATES[program_type]


# ---------- API ----------
def test_home_and_health(client):
    assert client.get("/").get_json()["app"] == "ACEest Fitness & Gym"
    assert client.get("/health").get_json() == {"status": "ok"}


def test_programs(client):
    assert set(client.get("/programs").get_json()) == {"FL", "MG", "BG"}
    assert client.get("/programs/mg").get_json()["calorie_factor"] == 35
    assert client.get("/programs/XX").status_code == 404


def test_login(client):
    assert client.post("/login", json={"username": "admin", "password": "admin"}).get_json()["role"] == "Admin"
    assert client.post("/login", json={"username": "admin", "password": "wrong"}).status_code == 401


def test_create_client_calculates_calories(ravi):
    data = ravi.get("/clients/Ravi").get_json()
    assert data["calories"] == 1540 and data["membership_status"] == "Active"
    assert len(ravi.get("/clients").get_json()) == 1


def test_create_client_validation(client):
    assert client.post("/clients", json={"name": "X"}).status_code == 400
    assert client.post("/clients", json={"name": "X", "program": "FL", "weight": -5}).status_code == 400
    assert client.get("/clients/Nobody").status_code == 404


def test_progress(ravi):
    assert ravi.post("/clients/Ravi/progress", json={"week": "Week 1", "adherence": 85}).status_code == 201
    assert ravi.get("/clients/Ravi/progress").get_json() == [{"week": "Week 1", "adherence": 85}]
    assert ravi.post("/clients/Ravi/progress", json={"adherence": 150}).status_code == 400


def test_workouts(ravi):
    r = ravi.post("/clients/Ravi/workouts", json={"workout_type": "Strength", "duration_min": 45})
    assert r.status_code == 201
    assert ravi.get("/clients/Ravi/workouts").get_json()[0]["workout_type"] == "Strength"
    assert ravi.post("/clients/Ravi/workouts", json={}).status_code == 400


def test_metrics_update_weight_and_bmi(ravi):
    assert ravi.post("/clients/Ravi/metrics", json={"weight": 85, "waist": 90}).status_code == 201
    assert ravi.get("/clients/Ravi/bmi").get_json()["category"] == "Overweight"
    assert ravi.post("/clients/Ravi/metrics", json={}).status_code == 400


def test_membership_endpoint(ravi):
    assert ravi.get("/clients/Ravi/membership").get_json()["status"] == "Active"


def test_generate_program_endpoint(ravi):
    data = ravi.post("/clients/Ravi/generate-program").get_json()
    assert data["program"] in PROGRAM_TEMPLATES[data["program_type"]]
    assert ravi.post("/clients/Nobody/generate-program").status_code == 404
