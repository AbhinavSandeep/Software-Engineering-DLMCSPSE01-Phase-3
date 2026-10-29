"""Configuration classes. Values come from environment variables so that the
same code runs locally, in Docker and in the cloud (twelve-factor style)."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'xptoirl.db'}")
    # Some hosting providers still hand out the old "postgres://" scheme.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
    MAX_SELECTED_SKILLS = 3
    # Ratings only influence the score once a game has enough of them.
    MIN_RATINGS_FOR_SCORE = 3
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


CONFIGS = {
    "development": Config,
    "production": ProductionConfig,
    "testing": TestConfig,
}
