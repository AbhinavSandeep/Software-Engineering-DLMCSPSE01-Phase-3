"""User and rating service: accounts (FR7), learning plan (FR8),
effectiveness ratings (FR9) and account deletion (NFR8, GDPR)."""

import re
from collections import OrderedDict

from sqlalchemy import select

from ..extensions import db
from ..models import Favourite, Game, Rating, Skill, User
from . import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def register(email: str, password: str, role: str = "user") -> User:
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise ValidationError("Please enter a valid e-mail address.")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"The password needs at least {MIN_PASSWORD_LENGTH} characters.")
    if db.session.scalar(select(User).where(User.email == email)):
        raise ValidationError("An account with this e-mail address already exists.")
    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(email: str, password: str) -> User | None:
    user = db.session.scalar(select(User).where(User.email == (email or "").strip().lower()))
    if user and user.check_password(password or ""):
        return user
    return None


def delete_account(user: User) -> None:
    """Remove the user together with favourites and ratings."""
    db.session.delete(user)
    db.session.commit()


# ---------------------------------------------------------------- learning plan

def is_favourite(user: User, game: Game, skill: Skill) -> bool:
    return _favourite(user, game, skill) is not None


def _favourite(user, game, skill):
    return db.session.scalar(
        select(Favourite).where(
            Favourite.user_id == user.id, Favourite.game_id == game.id, Favourite.skill_id == skill.id
        )
    )


def toggle_favourite(user: User, game: Game, skill: Skill) -> bool:
    """Add the game to the plan for this skill, or remove it. Returns the new state."""
    existing = _favourite(user, game, skill)
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return False
    db.session.add(Favourite(user=user, game=game, skill=skill))
    db.session.commit()
    return True


def learning_plan(user: User) -> "OrderedDict[Skill, list[Favourite]]":
    """The user's favourites grouped by skill, skills in alphabetical order."""
    favourites = db.session.scalars(
        select(Favourite).join(Favourite.skill).where(Favourite.user_id == user.id).order_by(Skill.name)
    ).all()
    plan: OrderedDict = OrderedDict()
    for fav in favourites:
        plan.setdefault(fav.skill, []).append(fav)
    return plan


# ---------------------------------------------------------------- ratings

def rate(user: User, game: Game, skill: Skill, score) -> Rating:
    """Store one rating per user, game and skill; a second rating updates it."""
    try:
        score = int(score)
    except (TypeError, ValueError):
        raise ValidationError("A rating must be a number from 1 to 5.") from None
    if not 1 <= score <= 5:
        raise ValidationError("A rating must be a number from 1 to 5.")
    if not any(m.skill_id == skill.id for m in game.mappings):
        raise ValidationError(f"'{game.title}' is not listed for '{skill.name}'.")
    rating = db.session.scalar(
        select(Rating).where(Rating.user_id == user.id, Rating.game_id == game.id, Rating.skill_id == skill.id)
    )
    if rating is None:
        rating = Rating(user=user, game=game, skill=skill, score=score)
        db.session.add(rating)
    else:
        rating.score = score
    db.session.commit()
    return rating


def user_ratings(user: User, game: Game) -> dict[int, int]:
    """The user's own scores for one game, keyed by skill id."""
    rows = db.session.scalars(select(Rating).where(Rating.user_id == user.id, Rating.game_id == game.id))
    return {r.skill_id: r.score for r in rows}
