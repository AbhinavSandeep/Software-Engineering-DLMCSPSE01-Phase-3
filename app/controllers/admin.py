"""Admin area (FR10, FR11): maintain skills, games, sources and mappings
without code changes. Only users with the role 'admin' have access."""

from functools import wraps

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from wtforms.fields.choices import SelectChoice

from ..extensions import db
from ..forms import GameForm, MappingForm, SkillForm, SourceForm
from ..models import Game, Skill, SkillGameMapping, Source
from ..services import ValidationError, catalogue, importer

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def _get_or_404(model, entity_id):
    entity = db.session.get(model, entity_id)
    if entity is None:
        abort(404)
    return entity


@bp.get("/")
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        counts=catalogue.counts(),
        skills=db.session.scalars(select(Skill).order_by(Skill.name)).all(),
        games=db.session.scalars(select(Game).order_by(Game.title)).all(),
        sources=db.session.scalars(select(Source).order_by(Source.key)).all(),
        mappings=db.session.scalars(
            select(SkillGameMapping).join(SkillGameMapping.game).order_by(Game.title)
        ).all(),
    )


# ---------------------------------------------------------------- skills

@bp.route("/skills/new", methods=["GET", "POST"], defaults={"skill_id": None})
@bp.route("/skills/<int:skill_id>", methods=["GET", "POST"])
@admin_required
def skill_form(skill_id):
    skill = _get_or_404(Skill, skill_id) if skill_id else None
    form = SkillForm(obj=skill)
    if form.validate_on_submit():
        try:
            catalogue.save_skill(skill, form.name.data, form.category.data, form.description.data)
        except ValidationError as exc:
            form.name.errors.append(str(exc))
        else:
            flash("Skill saved.", "success")
            return redirect(url_for("admin.dashboard", _anchor="skills"))
    return render_template("admin/form.html", form=form, title="Skill", entity=skill,
                           delete_url=url_for("admin.delete", kind="skill", entity_id=skill.id) if skill else None)


# ---------------------------------------------------------------- games

@bp.route("/games/new", methods=["GET", "POST"], defaults={"game_id": None})
@bp.route("/games/<int:game_id>", methods=["GET", "POST"])
@admin_required
def game_form(game_id):
    game = _get_or_404(Game, game_id) if game_id else None
    form = GameForm(obj=game)
    if game and request.method == "GET":
        form.pegi.data = str(game.pegi)
    if form.validate_on_submit():
        data = {name: field.data for name, field in form._fields.items() if name != "csrf_token"}
        try:
            catalogue.save_game(game, data)
        except ValidationError as exc:
            form.title.errors.append(str(exc))
        else:
            flash("Game saved.", "success")
            return redirect(url_for("admin.dashboard", _anchor="games"))
    return render_template("admin/form.html", form=form, title="Game", entity=game,
                           delete_url=url_for("admin.delete", kind="game", entity_id=game.id) if game else None)


# ---------------------------------------------------------------- sources

@bp.route("/sources/new", methods=["GET", "POST"], defaults={"source_id": None})
@bp.route("/sources/<int:source_id>", methods=["GET", "POST"])
@admin_required
def source_form(source_id):
    source = _get_or_404(Source, source_id) if source_id else None
    form = SourceForm(obj=source)
    if form.validate_on_submit():
        try:
            catalogue.save_source(source, form.key.data, form.citation.data, form.url.data, form.evidence.data)
        except ValidationError as exc:
            form.key.errors.append(str(exc))
        else:
            flash("Source saved.", "success")
            return redirect(url_for("admin.dashboard", _anchor="sources"))
    return render_template("admin/form.html", form=form, title="Source", entity=source,
                           delete_url=url_for("admin.delete", kind="source", entity_id=source.id) if source else None)


# ---------------------------------------------------------------- mappings

@bp.route("/mappings/new", methods=["GET", "POST"], defaults={"mapping_id": None})
@bp.route("/mappings/<int:mapping_id>", methods=["GET", "POST"])
@admin_required
def mapping_form(mapping_id):
    mapping = _get_or_404(SkillGameMapping, mapping_id) if mapping_id else None
    form = MappingForm(obj=mapping)
    form.skill.choices = [SelectChoice(s.id, s.name) for s in db.session.scalars(select(Skill).order_by(Skill.name))]
    form.game.choices = [SelectChoice(g.id, g.title) for g in db.session.scalars(select(Game).order_by(Game.title))]
    sources = db.session.scalars(select(Source).order_by(Source.key))
    form.sources.choices = [SelectChoice(s.id, f"{s.key} ({s.evidence})") for s in sources]
    if mapping and request.method == "GET":
        form.skill.data, form.game.data = mapping.skill_id, mapping.game_id
        form.strength.data = str(mapping.strength)
        form.sources.data = [s.id for s in mapping.sources]
    if form.validate_on_submit():
        sources = [db.session.get(Source, sid) for sid in form.sources.data]
        try:
            catalogue.save_mapping(mapping, db.session.get(Skill, form.skill.data), db.session.get(Game, form.game.data),
                                   form.strength.data, form.reason.data, [s for s in sources if s])
        except ValidationError as exc:
            form.reason.errors.append(str(exc))
        else:
            flash("Mapping saved.", "success")
            return redirect(url_for("admin.dashboard", _anchor="mappings"))
    return render_template("admin/form.html", form=form, title="Mapping", entity=mapping,
                           delete_url=url_for("admin.delete", kind="mapping", entity_id=mapping.id) if mapping else None)


# ---------------------------------------------------------------- delete and import

MODELS = {"skill": Skill, "game": Game, "source": Source, "mapping": SkillGameMapping}


@bp.post("/<kind>/<int:entity_id>/delete")
@admin_required
def delete(kind, entity_id):
    if kind not in MODELS:
        abort(404)
    try:
        catalogue.delete(_get_or_404(MODELS[kind], entity_id))
    except ValidationError as exc:
        flash(str(exc), "warning")
    else:
        flash(f"The {kind} was deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.post("/import")
@admin_required
def run_import():
    try:
        report = importer.import_directory(current_app.config["DATA_DIR"])
    except ValidationError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Import finished: {report.summary()}.", "success")
    return redirect(url_for("admin.dashboard"))
