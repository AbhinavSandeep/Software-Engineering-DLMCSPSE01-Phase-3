"""Filter service (FR4): narrows a game query by platform, genre, PEGI age,
price model, play mode and session length."""

from dataclasses import asdict, dataclass

from ..models import PLAY_MODES, PRICE_MODELS, Game

PEGI_VALUES = (3, 7, 12, 16, 18)


@dataclass(frozen=True)
class GameFilter:
    platform: str | None = None
    genre: str | None = None
    pegi_max: int | None = None
    price_model: str | None = None
    play_mode: str | None = None
    max_session: int | None = None

    @classmethod
    def from_args(cls, args) -> "GameFilter":
        """Build a filter from request arguments. Unknown or malformed values
        are ignored instead of raising, so a bad URL never breaks the page."""

        def text(name):
            value = (args.get(name) or "").strip()
            return value or None

        def number(name):
            try:
                return int(args.get(name, ""))
            except (TypeError, ValueError):
                return None

        pegi = number("pegi_max")
        price = text("price_model")
        mode = text("play_mode")
        session = number("max_session")
        return cls(
            platform=text("platform"),
            genre=text("genre"),
            pegi_max=pegi if pegi in PEGI_VALUES else None,
            price_model=price if price in PRICE_MODELS else None,
            play_mode=mode if mode in PLAY_MODES else None,
            max_session=session if session and session > 0 else None,
        )

    @property
    def is_active(self) -> bool:
        return any(v is not None for v in asdict(self).values())

    def as_args(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def apply(self, query):
        """Add the filter conditions to a SQLAlchemy select on Game."""
        if self.platform:
            query = query.where(Game.platforms.contains(self.platform))
        if self.genre:
            query = query.where(Game.genre == self.genre)
        if self.pegi_max is not None:
            query = query.where(Game.pegi <= self.pegi_max)
        if self.price_model:
            query = query.where(Game.price_model == self.price_model)
        if self.play_mode:
            # A game playable both ways matches either choice.
            query = query.where(Game.play_mode.in_((self.play_mode, "both")))
        if self.max_session is not None:
            query = query.where(Game.session_minutes <= self.max_session)
        return query
