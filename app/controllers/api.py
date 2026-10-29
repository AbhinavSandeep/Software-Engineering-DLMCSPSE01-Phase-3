"""Small read-only JSON API, used by the health check and for integration."""

from flask import Blueprint, jsonify, request
from sqlalchemy import select, text

from ..extensions import db
from ..models import Skill
from ..services import ValidationError, recommendation
from ..services.filters import GameFilter

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    db.session.execute(text("SELECT 1"))
    return jsonify(status="ok")


@bp.get("/skills")
def skills():
    rows = db.session.scalars(select(Skill).order_by(Skill.name))
    return jsonify([{"slug": s.slug, "name": s.name, "category": s.category} for s in rows])


@bp.get("/recommendations")
def recommendations():
    try:
        selected = recommendation.resolve_skills(request.args.getlist("skill"))
    except ValidationError as exc:
        return jsonify(error=str(exc)), 400
    results = recommendation.recommend(selected, GameFilter.from_args(request.args))
    return jsonify(
        [
            {
                "game": r.game.title,
                "slug": r.game.slug,
                "score": r.score,
                "evidence": r.best_evidence,
                "reasons": {m.skill.slug: m.reason for m in r.mappings},
                "sources": sorted({s.url for m in r.mappings for s in m.sources}),
            }
            for r in results
        ]
    )
