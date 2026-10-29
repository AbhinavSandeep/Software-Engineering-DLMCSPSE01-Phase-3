"""Recommendation service (FR2, FR3): ranks games for 1 to 3 selected skills.

The score is a transparent rule instead of a black-box model:

    score(g) = sum over selected skills s of  strength(g, s) * weight(evidence(g, s))
               + 0.5 * normalised average rating of g   (only with >= 3 ratings)

Evidence weights: A = 1.0, B = 0.7, C = 0.4. The normalised rating maps the
1..5 scale to -1..1, so poor ratings can lower a score as well as raise it.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from flask import current_app
from sqlalchemy import func, select

from ..extensions import db
from ..models import EVIDENCE_WEIGHTS, Game, Rating, Skill, SkillGameMapping
from . import ValidationError
from .filters import GameFilter

RATING_WEIGHT = 0.5


@dataclass
class Recommendation:
    game: Game
    score: float
    mappings: list[SkillGameMapping] = field(default_factory=list)
    rating_avg: float | None = None
    rating_count: int = 0

    @property
    def source_count(self) -> int:
        return len({s.id for m in self.mappings for s in m.sources})

    @property
    def best_evidence(self) -> str:
        return min((m.best_evidence for m in self.mappings), default="C")


def normalise_rating(avg: float) -> float:
    """Map an average rating on the 1..5 scale to -1..1."""
    return (avg - 3.0) / 2.0


def score_game(mappings, rating_avg: float | None, rating_count: int, min_ratings: int = 3) -> float:
    """Pure scoring function, kept free of database access for unit tests."""
    score = sum(m.strength * EVIDENCE_WEIGHTS[m.best_evidence] for m in mappings)
    if rating_avg is not None and rating_count >= min_ratings:
        score += RATING_WEIGHT * normalise_rating(rating_avg)
    return round(score, 2)


def resolve_skills(slugs) -> list[Skill]:
    """Turn requested skill slugs into Skill objects and check the 1..3 limit."""
    unique = list(dict.fromkeys(s.strip() for s in slugs if s and s.strip()))
    limit = current_app.config["MAX_SELECTED_SKILLS"]
    if not unique:
        raise ValidationError("Please choose at least one skill.")
    if len(unique) > limit:
        raise ValidationError(f"Please choose at most {limit} skills.")
    skills = db.session.scalars(select(Skill).where(Skill.slug.in_(unique))).all()
    if len(skills) != len(unique):
        raise ValidationError("One of the selected skills does not exist.")
    order = {slug: i for i, slug in enumerate(unique)}
    return sorted(skills, key=lambda s: order[s.slug])


def recommend(skills: list[Skill], game_filter: GameFilter | None = None) -> list[Recommendation]:
    """Return games that train at least one selected skill, best first."""
    skill_ids = [s.id for s in skills]
    query = (
        select(SkillGameMapping)
        .join(SkillGameMapping.game)
        .where(SkillGameMapping.skill_id.in_(skill_ids))
    )
    if game_filter is not None:
        query = game_filter.apply(query)

    by_game: dict[int, list[SkillGameMapping]] = defaultdict(list)
    for mapping in db.session.scalars(query):
        by_game[mapping.game_id].append(mapping)
    if not by_game:
        return []

    # Average rating per game over the selected skills, in one query.
    rating_rows = db.session.execute(
        select(Rating.game_id, func.avg(Rating.score), func.count(Rating.id))
        .where(Rating.game_id.in_(by_game.keys()), Rating.skill_id.in_(skill_ids))
        .group_by(Rating.game_id)
    ).all()
    ratings = {game_id: (float(avg), count) for game_id, avg, count in rating_rows}
    min_ratings = current_app.config["MIN_RATINGS_FOR_SCORE"]

    results = []
    for mappings in by_game.values():
        avg, count = ratings.get(mappings[0].game_id, (None, 0))
        results.append(
            Recommendation(
                game=mappings[0].game,
                score=score_game(mappings, avg, count, min_ratings),
                mappings=sorted(mappings, key=lambda m: skill_ids.index(m.skill_id)),
                rating_avg=avg,
                rating_count=count,
            )
        )
    # Highest score first; ties broken by the number of sources, then title.
    results.sort(key=lambda r: (-r.score, -r.source_count, r.game.title))
    return results
