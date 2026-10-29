# XPtoIRL: Experience Points to Real Life

XPtoIRL is a web application that recommends video games for the **real-life skills** a user wants to develop.
Users choose up to three skills (for example teamwork or spatial reasoning) and get a ranked list of games.
Every result shows a **reason**, an **evidence level** and the **source** that supports it.

Project for the IU course *Project: Software Engineering (DLMCSPSE01)*. Current release: **v1.0.0** (see `CHANGELOG.md`).

- Live application: <APP_URL>
- Source code: <GITHUB_URL>
- Installation and user manual (PDF): `docs/XPtoIRL_Installation_and_User_Manual.pdf`

## Features

| ID | Feature |
|----|---------|
| FR1 | Skill catalogue grouped by category (cognitive, social, motor, emotional) |
| FR2, FR3 | Recommendations for 1 to 3 skills with score, reason, evidence level and sources |
| FR4 | Filters: platform, genre, PEGI age, price model, play mode, session length |
| FR5, FR6 | Game detail page and search by game title |
| FR7 to FR9 | Accounts, learning plan per skill, effectiveness ratings (1 to 5) |
| FR10, FR11 | Admin area to maintain skills, games, sources and mappings; CSV import |
| FR12 | Printable learning plan |

The curated data set in `data/` contains 17 skills, 66 games, 175 skill-game mappings and 26 peer-reviewed or
expert sources. How the score is calculated is explained on the page *How it works* and in `docs/architecture.md`.

## Quick start with Docker (recommended)

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) with Docker Compose.

```bash
git clone https://github.com/<user_name>/xptoirl.git
cd xptoirl
docker compose up --build
```

Open <http://localhost:8000>. If port 8000 is already used on your PC, start with another host port, e.g.
`WEB_PORT=8010 docker compose up --build` (PowerShell: `$env:WEB_PORT=8010; docker compose up --build`).

On the first start the container applies the database migrations and imports the
data set. To create an administrator, set `ADMIN_EMAIL` and `ADMIN_PASSWORD` (see `.env.example`) or run:

```bash
docker compose exec web flask create-admin admin@example.org
```

## Local development without Docker

Requirements: Python 3.11 or newer. The app uses SQLite when `DATABASE_URL` is not set.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
set FLASK_APP=wsgi.py             # Windows  (macOS/Linux: export FLASK_APP=wsgi.py)
flask db upgrade
flask seed
flask create-admin admin@example.org
flask run
```

Open <http://127.0.0.1:5000>.

## Tests and quality checks

```bash
pytest --cov=app                  # 86 unit and integration tests
pytest --cov=app/services --cov-fail-under=70
ruff check .
python scripts/load_test.py --base-url http://localhost:8000 --users 20   # load test for NFR2
```

GitHub Actions runs the linter, the tests with the coverage gate and a Docker build for every push and pull request
(`.github/workflows/ci.yml`).

## Configuration

| Variable | Meaning | Default |
|----------|---------|---------|
| `APP_ENV` | `development`, `production` or `testing` | `development` |
| `SECRET_KEY` | Key for sessions and CSRF tokens; **required in production** | dev value |
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pw@host:5432/db` | local SQLite file |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Creates an administrator when the container starts | empty |
| `WEB_PORT` | Host port used by `docker compose` | `8000` |
| `PORT` | Port Gunicorn listens on inside the container (set by cloud platforms) | `8000` |

## Deployment to Render

The file `render.yaml` is a Render Blueprint. On the Render dashboard choose **New > Blueprint**, select the
repository, enter `ADMIN_EMAIL` and `ADMIN_PASSWORD` and confirm. Render then creates the PostgreSQL database and
the web service and sets `SECRET_KEY` and `DATABASE_URL` automatically.

Manual set-up without the Blueprint:

1. Push the repository to GitHub.
2. On [Render](https://render.com) create a **PostgreSQL** database and copy its *Internal Database URL*.
3. Create a **Web Service** from the repository with the runtime *Docker*.
4. Set the environment variables `APP_ENV=production`, `SECRET_KEY` (a long random string), `DATABASE_URL`
   (the URL from step 2), `ADMIN_EMAIL` and `ADMIN_PASSWORD`.
5. Deploy. The entry point runs `flask db upgrade` and `flask seed --if-empty` before Gunicorn starts.

## Project structure

```
app/
  controllers/   Flask Blueprints (HTTP layer)
  services/      business rules: recommendation, filters, catalogue, users, import
  models.py      SQLAlchemy models (data access layer)
  templates/     Jinja2 templates (presentation layer)
  static/        CSS and JavaScript
data/            curated CSV data set
migrations/      Alembic database migrations
tests/           pytest unit and integration tests
docs/            architecture documentation, design decisions, technical debt
scripts/         load test
```

## Third-party libraries

Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate (Alembic), SQLAlchemy, psycopg, Gunicorn and
Bootstrap 5 (loaded from the jsDelivr CDN). Development: pytest, pytest-cov, Ruff. All are open source; see
`docs/architecture.md` for versions, links and the reason for each choice.

## Using the application

1. On the start page choose one to three skills and press **Find games**.
2. Narrow the list with the filters (platform, genre, PEGI, price model, play mode, session length).
3. Open a game to read the reason, evidence level and sources for each skill.
4. Register to save games to your learning plan, rate how well a game trained a skill, and print the plan.
5. Administrators open **Admin** to edit skills, games, sources and mappings or to import CSV files.

## Technical debt

The known limitations of release 1.0 are listed in `docs/architecture.md`, section 8.

## Note on the data

Game facts (platforms, PEGI rating, price model) were entered by hand and should be checked against the official
pages before each release. Research on games and skills is mixed; many sources study a genre rather than a single
title, which the reason text and the lower strength make clear.
