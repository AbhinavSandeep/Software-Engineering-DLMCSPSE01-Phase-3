"""Shared fixtures: an app with an in-memory database and a small, known data set."""

import pytest

from app import create_app
from app.extensions import db
from app.services import importer, users

SKILLS = [
    {"name": "Teamwork", "category": "social", "description": "Working together."},
    {"name": "Communication", "category": "social", "description": "Talking clearly."},
    {"name": "Problem solving", "category": "cognitive", "description": "Solving problems."},
    {"name": "Reaction time", "category": "motor", "description": "Reacting fast."},
]
GAMES = [
    {"slug": "coop-kitchen", "title": "Coop Kitchen", "genre": "Co-op party", "platforms": "PC;Switch", "pegi": "3",
     "price_model": "paid", "play_mode": "both", "session_minutes": "20", "official_url": "https://example.org/a"},
    {"slug": "free-squad", "title": "Free Squad", "genre": "Team shooter", "platforms": "PC", "pegi": "16",
     "price_model": "free", "play_mode": "multi", "session_minutes": "30", "official_url": "https://example.org/b"},
    {"slug": "puzzle-box", "title": "Puzzle Box", "genre": "Puzzle", "platforms": "Mobile", "pegi": "7",
     "price_model": "free", "play_mode": "single", "session_minutes": "15", "official_url": "https://example.org/c"},
]
SOURCES = [
    {"key": "studyA", "citation": "Study A (2020).", "url": "https://doi.org/10.1/a", "evidence": "A"},
    {"key": "expertB", "citation": "Expert B (2021).", "url": "https://example.org/b", "evidence": "B"},
    {"key": "forumC", "citation": "Forum C (2022).", "url": "https://example.org/c", "evidence": "C"},
]
MAPPINGS = [
    # Coop Kitchen: teamwork 3*0.7 + communication 2*0.7 = 3.5 (the Phase 1 example)
    {"game": "coop-kitchen", "skill": "teamwork", "strength": "3", "reason": "Needs coordination.", "source_keys": "expertB"},
    {"game": "coop-kitchen", "skill": "communication", "strength": "2", "reason": "Players must talk.", "source_keys": "expertB"},
    # Free Squad: teamwork 2*1.0 = 2.0, reaction 3*1.0 = 3.0
    {"game": "free-squad", "skill": "teamwork", "strength": "2", "reason": "Team play.", "source_keys": "studyA"},
    {"game": "free-squad", "skill": "reaction-time", "strength": "3", "reason": "Fast action.", "source_keys": "studyA;forumC"},
    # Puzzle Box: problem solving 2*0.4 = 0.8, teamwork 1*0.4 = 0.4
    {"game": "puzzle-box", "skill": "problem-solving", "strength": "2", "reason": "Puzzles.", "source_keys": "forumC"},
    {"game": "puzzle-box", "skill": "teamwork", "strength": "1", "reason": "Share hints.", "source_keys": "forumC"},
]


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        importer.import_rows(SKILLS, GAMES, SOURCES, MAPPINGS)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    return users.register("lena@example.org", "secret-pass-1")


@pytest.fixture
def admin(app):
    return users.register("admin@example.org", "admin-pass-1", role="admin")


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


@pytest.fixture
def user_client(client, user):
    login(client, "lena@example.org", "secret-pass-1")
    return client


@pytest.fixture
def admin_client(client, admin):
    login(client, "admin@example.org", "admin-pass-1")
    return client
