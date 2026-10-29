"""Start page with the skill catalogue (FR1) and the 'How it works' page."""

from flask import Blueprint, render_template

from ..models import EVIDENCE_WEIGHTS
from ..services import catalogue

bp = Blueprint("catalogue", __name__)


@bp.get("/")
def index():
    return render_template(
        "index.html",
        skills_by_category=catalogue.skills_by_category(),
        counts=catalogue.counts(),
    )


@bp.get("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html", weights=EVIDENCE_WEIGHTS)
