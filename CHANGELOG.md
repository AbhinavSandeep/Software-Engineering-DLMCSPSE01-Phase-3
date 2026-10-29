# Changelog

The project follows semantic versioning. Each release is a Git tag.

## v1.0.0 (finalization phase)

- Render Blueprint `render.yaml` for a repeatable cloud deployment with PostgreSQL.
- Gunicorn listens on `$PORT`; `docker compose` host port can be changed with `WEB_PORT`.
- Load test script `scripts/load_test.py` (NFR2) and results in the architecture documentation.
- Automated accessibility check (axe-core, WCAG 2.1 AA) with 0 violations (NFR7).
- WTForms pinned; select fields use `SelectChoice`, which removes all deprecation warnings.
- README: usage guide, cloud deployment, configuration table; final technical debt list.

## v0.2.0 (development phase)

- Skill catalogue, recommendations with score, reason, evidence level and sources.
- Filters, search, game pages, accounts, learning plan, ratings, printable plan.
- Admin area, CSV import, JSON API, Alembic migrations, Docker, GitHub Actions CI.
- 86 automated tests, 93 % coverage of the service layer.
