# ACEest Fitness & Gym – DevOps CI/CD

A Flask REST service for gym management, ported from the ACEest Tkinter desktop baseline (v1.0–v3.2.4, kept in `legacy/`), delivered through an automated pipeline using Git, Pytest, Docker, Jenkins and GitHub Actions.

## Features (mapped from baseline versions)
| Baseline | Feature | Endpoint |
|---|---|---|
| v1.0 | Fat Loss / Muscle Gain / Beginner workout & diet plans | `/programs` |
| v1.1–1.1.2 | Calorie estimate (weight × program factor) | `POST /clients` |
| v2.0–2.2.1 | SQLite persistence, weekly adherence | `/clients`, `/progress` |
| v2.2.4–3.0.1 | Workout logging, body metrics, BMI | `/workouts`, `/metrics`, `/bmi` |
| v3.1.2–3.2.4 | Login, membership, program generator | `/login`, `/membership`, `/generate-program` |

## API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| GET | `/`, `/health` | App info and health check |
| GET | `/programs`, `/programs/<FL\|MG\|BG>` | Program list / workout & diet plan |
| POST | `/login` | Login (default `admin` / `admin`) |
| GET/POST | `/clients`, GET `/clients/<name>` | Client profiles with calorie estimate |
| GET/POST | `/clients/<name>/progress` | Weekly adherence (0–100%) |
| GET/POST | `/clients/<name>/workouts` | Workout log |
| POST | `/clients/<name>/metrics` | Body metrics (weight, waist, body fat) |
| GET | `/clients/<name>/bmi` | BMI with category and risk note |
| GET | `/clients/<name>/membership` | Membership status and renewal date |
| POST | `/clients/<name>/generate-program` | Random program from templates |

## Local Setup
```bash
git clone https://github.com/deenbenny/aceest-fitness-cicd.git
cd aceest-fitness-cicd
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py                     # http://localhost:5000
```
Example:
```bash
curl -X POST localhost:5000/clients -H "Content-Type: application/json" \
  -d '{"name":"Ravi","height":175,"weight":70,"program":"FL","membership_end":"2099-12-31"}'
curl localhost:5000/clients/Ravi/bmi
```

## Running Tests Manually
```bash
python -m pytest                              # local (19 tests)
docker build -t aceest-fitness .
docker run --rm aceest-fitness pytest         # inside the container
```

## Run with Docker
```bash
docker build -t aceest-fitness .
docker run -d -p 5000:5000 aceest-fitness
```
The image uses `python:3.12-slim`, runs as a non-root user, installs dependencies without pip cache and excludes non-runtime files (`legacy/`, `venv/`, `.git/`) via `.dockerignore`.

## CI/CD Overview
**GitHub Actions** (`.github/workflows/main.yml`) runs on every push and pull request:
1. **Build & Lint** – installs dependencies, runs flake8 syntax checks, compiles `app.py`.
2. **Docker Image Assembly** – builds the container image.
3. **Automated Testing** – runs the Pytest suite inside the container.

**Jenkins** (`Jenkinsfile`) is the secondary BUILD and quality gate. The job polls GitHub every 5 minutes, performs a clean checkout, creates a fresh virtual environment, lints, runs unit tests, builds the Docker image and runs the tests inside it, then cleans the workspace.

## Branching & Versioning
`main` (stable, tagged releases) ← `develop` (integration) ← `feature/*`, `infra/*`, `docs/*`, `chore/*`, merged via pull requests. Commits follow the Conventional Commits style; the baseline history is preserved as one commit per version under `legacy/`.
