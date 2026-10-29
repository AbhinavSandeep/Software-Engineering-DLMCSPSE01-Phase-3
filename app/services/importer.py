"""Import and validation service (FR11): loads the curated CSV data set.

The import is all-or-nothing. Every file is validated first; if any row is
invalid, nothing is written and all problems are reported together. Rows are
matched by slug or key, so running the import twice does not create duplicates.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from ..extensions import db
from ..models import Game, Skill, SkillGameMapping, Source
from . import ValidationError
from .catalogue import validate_game, validate_mapping, validate_skill, validate_source

FILES = ("skills.csv", "games.csv", "sources.csv", "mappings.csv")


@dataclass
class ImportReport:
    created: dict = field(default_factory=lambda: {"skills": 0, "games": 0, "sources": 0, "mappings": 0})
    updated: dict = field(default_factory=lambda: {"skills": 0, "games": 0, "sources": 0, "mappings": 0})

    def summary(self) -> str:
        parts = [f"{self.created[k]} new / {self.updated[k]} updated {k}" for k in self.created]
        return "; ".join(parts)


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def import_directory(data_dir: Path) -> ImportReport:
    data_dir = Path(data_dir)
    missing = [name for name in FILES if not (data_dir / name).exists()]
    if missing:
        raise ValidationError(f"Missing data files: {', '.join(missing)}")
    rows = {name: _read(data_dir / name) for name in FILES}
    return import_rows(rows["skills.csv"], rows["games.csv"], rows["sources.csv"], rows["mappings.csv"])


def import_rows(skill_rows, game_rows, source_rows, mapping_rows) -> ImportReport:
    errors: list[str] = []

    def check(fn, *args, line, file):
        try:
            return fn(*args)
        except ValidationError as exc:
            errors.append(f"{file}, line {line}: {exc}")
            return None

    skills = [check(validate_skill, r.get("name"), r.get("category"), r.get("description"), line=i, file="skills.csv")
              for i, r in enumerate(skill_rows, start=2)]
    games = [check(validate_game, r, line=i, file="games.csv") for i, r in enumerate(game_rows, start=2)]
    sources = [check(validate_source, r.get("key"), r.get("citation"), r.get("url"), r.get("evidence"),
                     line=i, file="sources.csv") for i, r in enumerate(source_rows, start=2)]

    skill_slugs = {s["slug"] for s in skills if s}
    game_slugs = {g["slug"] for g in games if g}
    source_keys = {s["key"] for s in sources if s}
    mappings = []
    for i, r in enumerate(mapping_rows, start=2):
        keys = [k.strip() for k in r.get("source_keys", "").split(";") if k.strip()]
        unknown = [k for k in keys if k not in source_keys]
        if r.get("skill") not in skill_slugs:
            errors.append(f"mappings.csv, line {i}: unknown skill '{r.get('skill')}'.")
        if r.get("game") not in game_slugs:
            errors.append(f"mappings.csv, line {i}: unknown game '{r.get('game')}'.")
        if unknown:
            errors.append(f"mappings.csv, line {i}: unknown source(s) {', '.join(unknown)}.")
        values = check(validate_mapping, r.get("strength"), r.get("reason"), keys, line=i, file="mappings.csv")
        if values:
            mappings.append((r.get("skill"), r.get("game"), values))

    if errors:
        raise ValidationError("The data set was not imported:\n" + "\n".join(errors))

    report = ImportReport()
    by_slug_skill = {s.slug: s for s in db.session.scalars(select(Skill))}
    by_slug_game = {g.slug: g for g in db.session.scalars(select(Game))}
    by_key_source = {s.key: s for s in db.session.scalars(select(Source))}

    def upsert(index, key, model, values, kind):
        obj = index.get(key)
        report.created[kind] += obj is None
        report.updated[kind] += obj is not None
        obj = obj or model()
        for k, v in values.items():
            setattr(obj, k, v)
        db.session.add(obj)
        index[key] = obj

    for values in skills:
        upsert(by_slug_skill, values["slug"], Skill, values, "skills")
    for values in games:
        upsert(by_slug_game, values["slug"], Game, values, "games")
    for values in sources:
        upsert(by_key_source, values["key"], Source, values, "sources")
    db.session.flush()

    existing = {(m.skill_id, m.game_id): m for m in db.session.scalars(select(SkillGameMapping))}
    for skill_slug, game_slug, values in mappings:
        skill, game = by_slug_skill[skill_slug], by_slug_game[game_slug]
        mapping = existing.get((skill.id, game.id))
        report.created["mappings"] += mapping is None
        report.updated["mappings"] += mapping is not None
        mapping = mapping or SkillGameMapping(skill=skill, game=game)
        mapping.strength = values["strength"]
        mapping.reason = values["reason"]
        mapping.sources = [by_key_source[k] for k in values["sources"]]
        db.session.add(mapping)
    db.session.commit()
    return report
