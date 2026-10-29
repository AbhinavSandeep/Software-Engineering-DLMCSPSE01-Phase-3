"""Data access layer: SQLAlchemy models of the XPtoIRL domain.

The many-to-many relation between skills and games is the association class
SkillGameMapping. Every mapping must cite at least one Source (NFR9); this is
checked in the import and admin services before a mapping is saved.
"""

from datetime import UTC, datetime

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

SKILL_CATEGORIES = ("cognitive", "social", "motor", "emotional")
PRICE_MODELS = ("free", "paid", "subscription")
PLAY_MODES = ("single", "multi", "both")
EVIDENCE_LEVELS = ("A", "B", "C")
# Weight of each evidence level in the recommendation score (Phase 1, 3.3).
EVIDENCE_WEIGHTS = {"A": 1.0, "B": 0.7, "C": 0.4}


def _now() -> datetime:
    return datetime.now(UTC)


mapping_sources = db.Table(
    "mapping_sources",
    db.Column("mapping_id", db.ForeignKey("skill_game_mapping.id", ondelete="CASCADE"), primary_key=True),
    db.Column("source_id", db.ForeignKey("source.id", ondelete="CASCADE"), primary_key=True),
)


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    name = db.Column(db.String(80), unique=True, nullable=False)
    category = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")

    mappings = db.relationship("SkillGameMapping", back_populates="skill", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint(f"category IN {SKILL_CATEGORIES}", name="ck_skill_category"),)

    def __repr__(self) -> str:
        return f"<Skill {self.slug}>"


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    genre = db.Column(db.String(40), nullable=False)
    # Stored as a semicolon-separated list, e.g. "PC;PlayStation;Switch".
    platforms = db.Column(db.String(200), nullable=False)
    pegi = db.Column(db.Integer, nullable=False)
    price_model = db.Column(db.String(20), nullable=False)
    play_mode = db.Column(db.String(10), nullable=False)
    session_minutes = db.Column(db.Integer, nullable=False)
    official_url = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")

    mappings = db.relationship("SkillGameMapping", back_populates="game", cascade="all, delete-orphan")
    ratings = db.relationship("Rating", back_populates="game", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("pegi IN (3, 7, 12, 16, 18)", name="ck_game_pegi"),
        CheckConstraint(f"price_model IN {PRICE_MODELS}", name="ck_game_price"),
        CheckConstraint(f"play_mode IN {PLAY_MODES}", name="ck_game_mode"),
        CheckConstraint("session_minutes > 0", name="ck_game_session"),
    )

    @property
    def platform_list(self) -> list[str]:
        return [p.strip() for p in self.platforms.split(";") if p.strip()]

    def __repr__(self) -> str:
        return f"<Game {self.slug}>"


class Source(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False)
    citation = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(300), nullable=False)
    evidence = db.Column(db.String(1), nullable=False)

    __table_args__ = (CheckConstraint(f"evidence IN {EVIDENCE_LEVELS}", name="ck_source_evidence"),)

    def __repr__(self) -> str:
        return f"<Source {self.key}>"


class SkillGameMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.ForeignKey("skill.id", ondelete="CASCADE"), nullable=False)
    game_id = db.Column(db.ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    strength = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)

    skill = db.relationship("Skill", back_populates="mappings")
    game = db.relationship("Game", back_populates="mappings")
    sources = db.relationship("Source", secondary=mapping_sources, lazy="selectin")

    __table_args__ = (
        UniqueConstraint("skill_id", "game_id", name="uq_mapping_skill_game"),
        CheckConstraint("strength BETWEEN 1 AND 3", name="ck_mapping_strength"),
    )

    @property
    def best_evidence(self) -> str:
        """Strongest evidence level among the cited sources (A > B > C)."""
        levels = sorted(s.evidence for s in self.sources)
        return levels[0] if levels else "C"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)

    favourites = db.relationship("Favourite", back_populates="user", cascade="all, delete-orphan")
    ratings = db.relationship("Rating", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint("role IN ('user', 'admin')", name="ck_user_role"),)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Favourite(db.Model):
    """An entry of a user's learning plan: a game saved for one skill."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    game_id = db.Column(db.ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    skill_id = db.Column(db.ForeignKey("skill.id", ondelete="CASCADE"), nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)

    user = db.relationship("User", back_populates="favourites")
    game = db.relationship("Game")
    skill = db.relationship("Skill")

    __table_args__ = (UniqueConstraint("user_id", "game_id", "skill_id", name="uq_favourite"),)


class Rating(db.Model):
    """A user's rating (1 to 5) of how well a game trained one skill."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    game_id = db.Column(db.ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    skill_id = db.Column(db.ForeignKey("skill.id", ondelete="CASCADE"), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_now)

    user = db.relationship("User", back_populates="ratings")
    game = db.relationship("Game", back_populates="ratings")
    skill = db.relationship("Skill")

    __table_args__ = (
        UniqueConstraint("user_id", "game_id", "skill_id", name="uq_rating"),
        CheckConstraint("score BETWEEN 1 AND 5", name="ck_rating_score"),
    )
