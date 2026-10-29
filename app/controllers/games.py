"""Game detail page (FR5) and game search (FR6)."""

from flask import Blueprint, abort, render_template, request
from flask_login import current_user

from ..services import catalogue, users

bp = Blueprint("games", __name__)


@bp.get("/games/<slug>")
def detail(slug):
    game = catalogue.get_game(slug)
    if game is None:
        abort(404)
    mappings = sorted(game.mappings, key=lambda m: (-m.strength, m.skill.name))
    own_ratings, saved = {}, set()
    if current_user.is_authenticated:
        own_ratings = users.user_ratings(current_user, game)
        saved = {f.skill_id for f in current_user.favourites if f.game_id == game.id}
    return render_template(
        "game_detail.html",
        game=game,
        mappings=mappings,
        ratings=catalogue.rating_summary(game),
        own_ratings=own_ratings,
        saved=saved,
    )


@bp.get("/search")
def search():
    term = request.args.get("q", "")
    return render_template("search.html", term=term, games=catalogue.search_games(term))
