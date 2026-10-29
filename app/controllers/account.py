"""Learning plan (FR8, FR12), effectiveness ratings (FR9) and account deletion (NFR8)."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from ..extensions import db
from ..models import Game, Skill
from ..services import ValidationError, users
from . import safe_next

bp = Blueprint("account", __name__)


def _game_and_skill():
    game = db.session.get(Game, request.form.get("game_id", type=int))
    skill = db.session.get(Skill, request.form.get("skill_id", type=int))
    if game is None or skill is None:
        abort(404)
    return game, skill


@bp.get("/plan")
@login_required
def plan():
    return render_template("account/plan.html", plan=users.learning_plan(current_user))


@bp.get("/plan/print")
@login_required
def plan_print():
    return render_template("account/plan_print.html", plan=users.learning_plan(current_user))


@bp.post("/plan/toggle")
@login_required
def toggle():
    game, skill = _game_and_skill()
    added = users.toggle_favourite(current_user, game, skill)
    flash(f"'{game.title}' {'saved to' if added else 'removed from'} your plan for {skill.name}.", "success")
    return redirect(safe_next("account.plan"))


@bp.post("/rate")
@login_required
def rate():
    game, skill = _game_and_skill()
    try:
        users.rate(current_user, game, skill, request.form.get("score"))
    except ValidationError as exc:
        flash(str(exc), "warning")
    else:
        flash(f"Thank you! Your rating for {skill.name} was saved.", "success")
    return redirect(url_for("games.detail", slug=game.slug))


@bp.get("/account")
@login_required
def settings():
    return render_template("account/settings.html")


@bp.post("/account/delete")
@login_required
def delete():
    if request.form.get("confirm") != "DELETE":
        flash("Type DELETE to confirm that your account should be removed.", "warning")
        return redirect(url_for("account.settings"))
    user = current_user._get_current_object()
    logout_user()
    users.delete_account(user)
    flash("Your account and all your data were deleted.", "info")
    return redirect(url_for("catalogue.index"))
