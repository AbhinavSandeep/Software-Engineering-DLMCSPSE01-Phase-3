"""Result page: recommendations for the selected skills (FR2, FR3, FR4)."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..services import ValidationError, catalogue, recommendation
from ..services.filters import GameFilter

bp = Blueprint("recommend", __name__)


@bp.get("/recommend")
def results():
    try:
        skills = recommendation.resolve_skills(request.args.getlist("skill"))
    except ValidationError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("catalogue.index"))

    game_filter = GameFilter.from_args(request.args)
    results = recommendation.recommend(skills, game_filter)

    saved = set()
    if current_user.is_authenticated:
        saved = {(f.game_id, f.skill_id) for f in current_user.favourites}

    return render_template(
        "results.html",
        skills=skills,
        results=results,
        game_filter=game_filter,
        options=catalogue.filter_options(),
        saved=saved,
    )
