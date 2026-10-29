"""Unit tests of the filter service (FR4)."""

from sqlalchemy import select

from app.extensions import db
from app.models import Game
from app.services.filters import GameFilter


def titles(game_filter):
    return {g.slug for g in db.session.scalars(game_filter.apply(select(Game)))}


def test_from_args_reads_valid_values():
    f = GameFilter.from_args({"platform": "PC", "pegi_max": "12", "price_model": "free", "max_session": "30"})
    assert f == GameFilter(platform="PC", pegi_max=12, price_model="free", max_session=30)
    assert f.is_active


def test_from_args_ignores_invalid_values():
    f = GameFilter.from_args({"pegi_max": "13", "price_model": "cheap", "play_mode": "x", "max_session": "-5"})
    assert f == GameFilter()
    assert not f.is_active


def test_as_args_only_contains_set_values():
    assert GameFilter(genre="Puzzle").as_args() == {"genre": "Puzzle"}


def test_fr4_pegi_and_price(app):
    # Acceptance criterion FR4: PEGI <= 12 and free to play hides PEGI 16 and paid games.
    assert titles(GameFilter(pegi_max=12, price_model="free")) == {"puzzle-box"}


def test_platform(app):
    assert titles(GameFilter(platform="Switch")) == {"coop-kitchen"}


def test_play_mode_matches_both(app):
    assert titles(GameFilter(play_mode="multi")) == {"coop-kitchen", "free-squad"}


def test_session_and_genre(app):
    assert titles(GameFilter(max_session=20)) == {"coop-kitchen", "puzzle-box"}
    assert titles(GameFilter(genre="Puzzle")) == {"puzzle-box"}
