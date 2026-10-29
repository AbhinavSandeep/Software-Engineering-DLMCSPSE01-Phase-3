"""Unit tests of the catalogue service (FR1, FR5, FR6, FR10)."""

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Game, Skill, Source
from app.services import ValidationError, catalogue

GAME = {"title": "New Game", "genre": "Puzzle", "platforms": "PC; Switch", "pegi": "7", "price_model": "paid",
        "play_mode": "single", "session_minutes": "25", "official_url": "https://example.org/new"}


def test_slugify():
    assert catalogue.slugify("Overcooked! 2") == "overcooked-2"


def test_skills_are_grouped_by_category(app):
    grouped = catalogue.skills_by_category()
    assert list(grouped) == ["cognitive", "social", "motor"]
    assert [s.name for s in grouped["social"]] == ["Communication", "Teamwork"]


def test_fr6_search_by_name(app):
    assert [g.slug for g in catalogue.search_games("puzzle")] == ["puzzle-box"]
    assert catalogue.search_games("p") == []


def test_filter_options_come_from_data(app):
    options = catalogue.filter_options()
    assert options["platforms"] == ["Mobile", "PC", "Switch"]
    assert "Puzzle" in options["genres"]


def test_save_game_cleans_platforms(app):
    game = catalogue.save_game(None, GAME)
    assert game.slug == "new-game" and game.platforms == "PC;Switch"


@pytest.mark.parametrize("field,value", [("pegi", "10"), ("price_model", "cheap"), ("official_url", "ftp://x"),
                                         ("platforms", " ; "), ("session_minutes", "0")])
def test_save_game_validates(app, field, value):
    with pytest.raises(ValidationError):
        catalogue.save_game(None, {**GAME, field: value})


def test_duplicate_skill_is_rejected(app):
    with pytest.raises(ValidationError, match="already exists"):
        catalogue.save_skill(None, "Teamwork", "social", "")


def test_edit_skill_keeps_its_row(app):
    skill = db.session.scalar(select(Skill).where(Skill.slug == "teamwork"))
    catalogue.save_skill(skill, "Teamwork", "social", "Updated text")
    assert skill.description == "Updated text"


def test_mapping_needs_a_source(app):
    skill = db.session.scalar(select(Skill).where(Skill.slug == "communication"))
    game = db.session.scalar(select(Game).where(Game.slug == "puzzle-box"))
    with pytest.raises(ValidationError, match="at least one source"):
        catalogue.save_mapping(None, skill, game, 2, "reason", [])
    source = db.session.scalar(select(Source).where(Source.key == "studyA"))
    mapping = catalogue.save_mapping(None, skill, game, 2, "reason", [source])
    assert mapping.best_evidence == "A"


def test_source_in_use_cannot_be_deleted(app):
    source = db.session.scalar(select(Source).where(Source.key == "studyA"))
    with pytest.raises(ValidationError, match="still cited"):
        catalogue.delete(source)


def test_rating_summary(app, user):
    from app.services import users

    game = db.session.scalar(select(Game).where(Game.slug == "coop-kitchen"))
    skill = db.session.scalar(select(Skill).where(Skill.slug == "teamwork"))
    users.rate(user, game, skill, 4)
    assert catalogue.rating_summary(game) == {skill.id: (4.0, 1)}
