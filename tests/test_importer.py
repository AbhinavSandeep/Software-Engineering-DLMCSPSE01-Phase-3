"""Tests of the import and validation service (FR11, NFR9) and of the real data set."""

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Game, Skill, SkillGameMapping, Source
from app.services import ValidationError, importer

from .conftest import GAMES, MAPPINGS, SKILLS, SOURCES

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def count(model):
    return db.session.scalar(select(func.count(model.id)))


def test_import_is_idempotent(app):
    report = importer.import_rows(SKILLS, GAMES, SOURCES, MAPPINGS)
    assert report.created == {"skills": 0, "games": 0, "sources": 0, "mappings": 0}
    assert report.updated["mappings"] == len(MAPPINGS)
    assert count(SkillGameMapping) == len(MAPPINGS)


def test_import_updates_changed_values(app):
    changed = [dict(m) for m in MAPPINGS]
    changed[0]["reason"] = "New reason."
    importer.import_rows(SKILLS, GAMES, SOURCES, changed)
    mapping = db.session.scalars(select(SkillGameMapping)).first()
    assert mapping.reason == "New reason."


def test_nfr9_mapping_without_source_is_rejected(app):
    bad = MAPPINGS + [{"game": "puzzle-box", "skill": "communication", "strength": "1", "reason": "x", "source_keys": ""}]
    with pytest.raises(ValidationError, match="at least one source"):
        importer.import_rows(SKILLS, GAMES, SOURCES, bad)


def test_errors_are_collected_and_nothing_is_written(app):
    bad_games = GAMES + [{**GAMES[0], "slug": "new", "title": "New", "pegi": "13"}]
    bad_maps = MAPPINGS + [{"game": "ghost", "skill": "teamwork", "strength": "9", "reason": "", "source_keys": "nope"}]
    with pytest.raises(ValidationError) as exc:
        importer.import_rows(SKILLS, bad_games, SOURCES, bad_maps)
    message = str(exc.value)
    assert "games.csv, line" in message and "unknown game 'ghost'" in message and "unknown source" in message
    assert count(Game) == len(GAMES)


def test_missing_file_is_reported(app, tmp_path):
    with pytest.raises(ValidationError, match="Missing data files"):
        importer.import_directory(tmp_path)


def test_real_data_set_meets_phase1_objective_o2(app):
    """O2: at least 15 skills and 60 games, every mapping with at least one source."""
    db.drop_all()
    db.create_all()
    importer.import_directory(DATA_DIR)
    assert count(Skill) >= 15
    assert count(Game) >= 60
    assert count(Source) >= 1
    mappings = db.session.scalars(select(SkillGameMapping)).all()
    assert mappings and all(m.sources for m in mappings)
    assert all(skill.mappings for skill in db.session.scalars(select(Skill)))
    assert all(game.mappings for game in db.session.scalars(select(Game)))
