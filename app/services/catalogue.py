"""Catalogue service: read access to skills and games (FR1, FR5, FR6) and the
create/edit/delete rules used by the admin area (FR10)."""

import re

from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    EVIDENCE_LEVELS,
    PLAY_MODES,
    PRICE_MODELS,
    SKILL_CATEGORIES,
    Game,
    Rating,
    Skill,
    SkillGameMapping,
    Source,
)
from . import ValidationError
from .filters import PEGI_VALUES


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------- reading

def skills_by_category() -> dict[str, list[Skill]]:
    skills = db.session.scalars(select(Skill).order_by(Skill.name)).all()
    grouped = {category: [] for category in SKILL_CATEGORIES}
    for skill in skills:
        grouped[skill.category].append(skill)
    return {c: s for c, s in grouped.items() if s}


def get_skill(slug: str) -> Skill | None:
    return db.session.scalar(select(Skill).where(Skill.slug == slug))


def get_game(slug: str) -> Game | None:
    return db.session.scalar(select(Game).where(Game.slug == slug))


def search_games(term: str, limit: int = 30) -> list[Game]:
    term = (term or "").strip()
    if len(term) < 2:
        return []
    pattern = f"%{term.lower()}%"
    return db.session.scalars(
        select(Game).where(func.lower(Game.title).like(pattern)).order_by(Game.title).limit(limit)
    ).all()


def filter_options() -> dict:
    """Values for the filter drop-downs, taken from the data itself."""
    games = db.session.scalars(select(Game)).all()
    platforms = sorted({p for g in games for p in g.platform_list})
    genres = sorted({g.genre for g in games})
    return {
        "platforms": platforms,
        "genres": genres,
        "pegi": PEGI_VALUES,
        "price_models": PRICE_MODELS,
        "play_modes": PLAY_MODES,
        "sessions": (15, 30, 60, 120),
    }


def rating_summary(game: Game) -> dict[int, tuple[float, int]]:
    """Average rating and number of ratings per skill for one game (FR9)."""
    rows = db.session.execute(
        select(Rating.skill_id, func.avg(Rating.score), func.count(Rating.id))
        .where(Rating.game_id == game.id)
        .group_by(Rating.skill_id)
    ).all()
    return {skill_id: (round(float(avg), 1), count) for skill_id, avg, count in rows}


def counts() -> dict[str, int]:
    return {
        "skills": db.session.scalar(select(func.count(Skill.id))),
        "games": db.session.scalar(select(func.count(Game.id))),
        "mappings": db.session.scalar(select(func.count(SkillGameMapping.id))),
        "sources": db.session.scalar(select(func.count(Source.id))),
    }


# ---------------------------------------------------------------- validation

def _require(value, message):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(message)
    return value.strip() if isinstance(value, str) else value


def validate_skill(name, category, description) -> dict:
    name = _require(name, "A skill needs a name.")
    if category not in SKILL_CATEGORIES:
        raise ValidationError(f"Unknown skill category '{category}'.")
    return {"name": name, "slug": slugify(name), "category": category, "description": (description or "").strip()}


def validate_game(data: dict) -> dict:
    title = _require(data.get("title"), "A game needs a title.")
    try:
        pegi = int(data.get("pegi"))
        session = int(data.get("session_minutes"))
    except (TypeError, ValueError):
        raise ValidationError(f"PEGI and session length of '{title}' must be numbers.") from None
    if pegi not in PEGI_VALUES:
        raise ValidationError(f"PEGI of '{title}' must be one of {PEGI_VALUES}.")
    if session <= 0:
        raise ValidationError(f"Session length of '{title}' must be positive.")
    if data.get("price_model") not in PRICE_MODELS:
        raise ValidationError(f"Price model of '{title}' must be one of {PRICE_MODELS}.")
    if data.get("play_mode") not in PLAY_MODES:
        raise ValidationError(f"Play mode of '{title}' must be one of {PLAY_MODES}.")
    url = _require(data.get("official_url"), f"'{title}' needs an official URL.")
    if not url.startswith(("https://", "http://")):
        raise ValidationError(f"The URL of '{title}' must start with http:// or https://.")
    platforms = ";".join(p.strip() for p in str(data.get("platforms", "")).split(";") if p.strip())
    if not platforms:
        raise ValidationError(f"'{title}' needs at least one platform.")
    return {
        "title": title,
        "slug": data.get("slug") or slugify(title),
        "genre": _require(data.get("genre"), f"'{title}' needs a genre."),
        "platforms": platforms,
        "pegi": pegi,
        "price_model": data["price_model"],
        "play_mode": data["play_mode"],
        "session_minutes": session,
        "official_url": url,
        "description": (data.get("description") or "").strip(),
    }


def validate_source(key, citation, url, evidence) -> dict:
    key = _require(key, "A source needs a key.")
    if evidence not in EVIDENCE_LEVELS:
        raise ValidationError(f"Evidence level of source '{key}' must be A, B or C.")
    url = _require(url, f"Source '{key}' needs a URL.")
    if not url.startswith(("https://", "http://")):
        raise ValidationError(f"The URL of source '{key}' must start with http:// or https://.")
    return {"key": key, "citation": _require(citation, f"Source '{key}' needs a citation."), "url": url,
            "evidence": evidence}


def validate_mapping(strength, reason, sources) -> dict:
    try:
        strength = int(strength)
    except (TypeError, ValueError):
        raise ValidationError("Strength must be 1, 2 or 3.") from None
    if strength not in (1, 2, 3):
        raise ValidationError("Strength must be 1, 2 or 3.")
    reason = _require(reason, "Every mapping needs a reason.")
    if not sources:
        # NFR9: no recommendation without a source.
        raise ValidationError("Every mapping needs at least one source.")
    return {"strength": strength, "reason": reason, "sources": list(sources)}


# ---------------------------------------------------------------- writing (admin)

def save_skill(skill: Skill | None, name, category, description) -> Skill:
    values = validate_skill(name, category, description)
    clash = db.session.scalar(select(Skill).where(Skill.slug == values["slug"]))
    if clash and clash is not skill:
        raise ValidationError(f"A skill called '{values['name']}' already exists.")
    skill = skill or Skill()
    for k, v in values.items():
        setattr(skill, k, v)
    db.session.add(skill)
    db.session.commit()
    return skill


def save_game(game: Game | None, data: dict) -> Game:
    values = validate_game({**data, "slug": game.slug if game else None})
    clash = db.session.scalar(select(Game).where(Game.slug == values["slug"]))
    if clash and clash is not game:
        raise ValidationError(f"A game called '{values['title']}' already exists.")
    game = game or Game()
    for k, v in values.items():
        setattr(game, k, v)
    db.session.add(game)
    db.session.commit()
    return game


def save_source(source: Source | None, key, citation, url, evidence) -> Source:
    values = validate_source(key, citation, url, evidence)
    clash = db.session.scalar(select(Source).where(Source.key == values["key"]))
    if clash and clash is not source:
        raise ValidationError(f"A source with key '{values['key']}' already exists.")
    source = source or Source()
    for k, v in values.items():
        setattr(source, k, v)
    db.session.add(source)
    db.session.commit()
    return source


def save_mapping(mapping: SkillGameMapping | None, skill: Skill, game: Game, strength, reason,
                 sources: list[Source]) -> SkillGameMapping:
    values = validate_mapping(strength, reason, sources)
    clash = db.session.scalar(
        select(SkillGameMapping).where(SkillGameMapping.skill_id == skill.id, SkillGameMapping.game_id == game.id)
    )
    if clash and clash is not mapping:
        raise ValidationError(f"'{game.title}' is already mapped to '{skill.name}'.")
    mapping = mapping or SkillGameMapping()
    mapping.skill, mapping.game = skill, game
    mapping.strength, mapping.reason, mapping.sources = values["strength"], values["reason"], values["sources"]
    db.session.add(mapping)
    db.session.commit()
    return mapping


def delete(entity) -> None:
    if isinstance(entity, Source) and db.session.scalar(
        select(func.count()).select_from(SkillGameMapping).where(SkillGameMapping.sources.contains(entity))
    ):
        raise ValidationError("This source is still cited by a mapping. Remove it from the mappings first.")
    db.session.delete(entity)
    db.session.commit()
