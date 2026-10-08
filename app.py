"""ACEest Fitness & Gym - Flask web service.

Ported from the ACEest Tkinter desktop versions (1.0 to 3.2.4): programs,
calorie estimation, client profiles, weekly adherence, workout and body-metric
logging, BMI, membership and program generation, backed by SQLite.
"""
import os
import random
import sqlite3
from datetime import date

from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

APP_VERSION = "3.2.4"

PROGRAMS = {
    "FL": {
        "name": "Fat Loss",
        "workout": ["Mon: Back Squat 5x5 + Core", "Tue: EMOM 20min Assault Bike",
                    "Wed: Bench Press + 21-15-9", "Thu: Deadlift + Box Jumps",
                    "Fri: Zone 2 Cardio 30min"],
        "diet": ["Breakfast: Egg Whites + Oats", "Lunch: Grilled Chicken + Brown Rice",
                 "Dinner: Fish Curry + Millet Roti", "Target: ~2000 kcal"],
        "calorie_factor": 22,
    },
    "MG": {
        "name": "Muscle Gain",
        "workout": ["Mon: Squat 5x5", "Tue: Bench 5x5", "Wed: Deadlift 4x6",
                    "Thu: Front Squat 4x8", "Fri: Incline Press 4x10", "Sat: Barbell Rows 4x10"],
        "diet": ["Breakfast: Eggs + Peanut Butter Oats", "Lunch: Chicken Biryani",
                 "Dinner: Mutton Curry + Rice", "Target: ~3200 kcal"],
        "calorie_factor": 35,
    },
    "BG": {
        "name": "Beginner",
        "workout": ["Full Body Circuit: Air Squats, Ring Rows, Push-ups",
                    "Focus: Technique & Consistency"],
        "diet": ["Balanced Tamil Meals: Idli / Dosa / Rice + Dal", "Protein Target: 120g/day"],
        "calorie_factor": 26,
    },
}

PROGRAM_TEMPLATES = {
    "Fat Loss": ["Full Body HIIT", "Circuit Training", "Cardio + Weights"],
    "Muscle Gain": ["Push/Pull/Legs", "Upper/Lower Split", "Full Body Strength"],
    "Beginner": ["Full Body 3x/week", "Light Strength + Mobility"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, age INTEGER,
    height REAL, weight REAL, program TEXT, calories INTEGER,
    target_weight REAL, target_adherence INTEGER,
    membership_status TEXT, membership_end TEXT);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT, week TEXT, adherence INTEGER);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT, date TEXT,
    workout_type TEXT, duration_min INTEGER, notes TEXT);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT, date TEXT,
    weight REAL, waist REAL, bodyfat REAL);
"""


# ---------- core business logic (pure functions) ----------
def calculate_calories(weight_kg, program_code):
    if program_code not in PROGRAMS:
        raise ValueError("unknown program")
    if weight_kg <= 0:
        raise ValueError("weight must be positive")
    return int(weight_kg * PROGRAMS[program_code]["calorie_factor"])


def calculate_bmi(weight_kg, height_cm):
    if weight_kg <= 0 or height_cm <= 0:
        raise ValueError("weight and height must be positive")
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)
    if bmi < 18.5:
        category, risk = "Underweight", "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category, risk = "Normal", "Low risk if active and strong."
    elif bmi < 30:
        category, risk = "Overweight", "Moderate risk; focus on adherence and progressive activity."
    else:
        category, risk = "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."
    return {"bmi": bmi, "category": category, "risk": risk}


def membership_state(end_date, today=None):
    if not end_date:
        return "Inactive"
    today = today or date.today()
    return "Active" if date.fromisoformat(end_date) >= today else "Expired"


def generate_program(rng=random):
    program_type = rng.choice(list(PROGRAM_TEMPLATES))
    return program_type, rng.choice(PROGRAM_TEMPLATES[program_type])


# ---------- application factory ----------
def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("ACEEST_DB", "aceest_fitness.db")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        if not db.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
            db.execute("INSERT INTO users VALUES (?, ?, ?)",
                       ("admin", generate_password_hash("admin"), "Admin"))
        db.commit()

    def body():
        return request.get_json(silent=True) or {}

    def find_client(name):
        return get_db().execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()

    def not_found():
        return jsonify(error="client not found"), 404

    @app.get("/")
    def home():
        return jsonify(app="ACEest Fitness & Gym", version=APP_VERSION)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/programs")
    def list_programs():
        return jsonify({code: p["name"] for code, p in PROGRAMS.items()})

    @app.get("/programs/<code>")
    def program_detail(code):
        program = PROGRAMS.get(code.upper())
        if not program:
            return jsonify(error="program not found"), 404
        return jsonify(program)

    @app.post("/login")
    def login():
        data = body()
        row = get_db().execute("SELECT password, role FROM users WHERE username=?",
                               (data.get("username", ""),)).fetchone()
        if row and check_password_hash(row["password"], data.get("password", "")):
            return jsonify(username=data["username"], role=row["role"])
        return jsonify(error="invalid credentials"), 401

    @app.route("/clients", methods=["GET", "POST"])
    def clients():
        db = get_db()
        if request.method == "GET":
            rows = db.execute("SELECT name, program FROM clients ORDER BY name").fetchall()
            return jsonify([dict(r) for r in rows])
        data = body()
        name, program = (data.get("name") or "").strip(), data.get("program")
        if not name or program not in PROGRAMS:
            return jsonify(error="name and valid program (FL, MG, BG) required"), 400
        try:
            weight = float(data["weight"]) if data.get("weight") else None
            calories = calculate_calories(weight, program) if weight else None
        except (TypeError, ValueError) as e:
            return jsonify(error=str(e)), 400
        db.execute(
            """INSERT OR REPLACE INTO clients (name, age, height, weight, program, calories,
               target_weight, target_adherence, membership_status, membership_end)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, data.get("age"), data.get("height"), weight, program, calories,
             data.get("target_weight"), data.get("target_adherence"),
             membership_state(data.get("membership_end")), data.get("membership_end")))
        db.commit()
        return jsonify(dict(find_client(name))), 201

    @app.get("/clients/<name>")
    def client_detail(name):
        client = find_client(name)
        return jsonify(dict(client)) if client else not_found()

    @app.route("/clients/<name>/progress", methods=["GET", "POST"])
    def progress(name):
        if not find_client(name):
            return not_found()
        db = get_db()
        if request.method == "POST":
            adherence = body().get("adherence")
            if not isinstance(adherence, int) or not 0 <= adherence <= 100:
                return jsonify(error="adherence must be an integer 0-100"), 400
            week = body().get("week") or date.today().strftime("Week %U - %Y")
            db.execute("INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
                       (name, week, adherence))
            db.commit()
            return jsonify(client=name, week=week, adherence=adherence), 201
        rows = db.execute("SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id",
                          (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/clients/<name>/workouts", methods=["GET", "POST"])
    def workouts(name):
        if not find_client(name):
            return not_found()
        db = get_db()
        if request.method == "POST":
            data = body()
            if not data.get("workout_type"):
                return jsonify(error="workout_type required"), 400
            try:
                duration = int(data.get("duration_min", 60))
            except (TypeError, ValueError):
                return jsonify(error="duration_min must be an integer"), 400
            db.execute("""INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
                          VALUES (?, ?, ?, ?, ?)""",
                       (name, data.get("date") or date.today().isoformat(),
                        data["workout_type"], duration, data.get("notes", "")))
            db.commit()
            return jsonify(client=name, workout_type=data["workout_type"], duration_min=duration), 201
        rows = db.execute("""SELECT date, workout_type, duration_min, notes FROM workouts
                             WHERE client_name=? ORDER BY date DESC""", (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients/<name>/metrics")
    def metrics(name):
        if not find_client(name):
            return not_found()
        data = body()
        try:
            weight = float(data["weight"])
        except (KeyError, TypeError, ValueError):
            return jsonify(error="weight required"), 400
        db = get_db()
        db.execute("INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?, ?, ?, ?, ?)",
                   (name, data.get("date") or date.today().isoformat(), weight,
                    data.get("waist"), data.get("bodyfat")))
        db.execute("UPDATE clients SET weight=? WHERE name=?", (weight, name))
        db.commit()
        return jsonify(client=name, weight=weight), 201

    @app.get("/clients/<name>/bmi")
    def bmi(name):
        client = find_client(name)
        if not client:
            return not_found()
        try:
            return jsonify(client=name, **calculate_bmi(client["weight"] or 0, client["height"] or 0))
        except ValueError as e:
            return jsonify(error=str(e)), 400

    @app.get("/clients/<name>/membership")
    def membership(name):
        client = find_client(name)
        if not client:
            return not_found()
        return jsonify(client=name, status=membership_state(client["membership_end"]),
                       renewal_date=client["membership_end"])

    @app.post("/clients/<name>/generate-program")
    def generate(name):
        if not find_client(name):
            return not_found()
        program_type, detail = generate_program()
        db = get_db()
        db.execute("UPDATE clients SET program=? WHERE name=?", (detail, name))
        db.commit()
        return jsonify(client=name, program_type=program_type, program=detail)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
