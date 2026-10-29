"""Unit tests of the user and rating service (FR7, FR8, FR9, NFR8)."""

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Favourite, Game, Rating, Skill, User
from app.services import ValidationError, users


def get(model, slug):
    return db.session.scalar(select(model).where(model.slug == slug))


class TestAccounts:
    def test_password_is_hashed(self, user):
        assert user.password_hash != "secret-pass-1"
        assert user.check_password("secret-pass-1")

    def test_email_is_normalised(self, app):
        assert users.register("  Mixed@Example.ORG ", "password-123").email == "mixed@example.org"

    @pytest.mark.parametrize("email,password", [("no-at-sign", "password-123"), ("a@b.org", "short")])
    def test_invalid_input_is_rejected(self, app, email, password):
        with pytest.raises(ValidationError):
            users.register(email, password)

    def test_duplicate_email_is_rejected(self, user):
        with pytest.raises(ValidationError, match="already exists"):
            users.register("LENA@example.org", "another-pass")

    def test_authenticate(self, user):
        assert users.authenticate("lena@example.org", "secret-pass-1") == user
        assert users.authenticate("lena@example.org", "wrong") is None
        assert users.authenticate("nobody@example.org", "secret-pass-1") is None

    def test_nfr8_delete_account_removes_personal_data(self, user):
        game, skill = get(Game, "coop-kitchen"), get(Skill, "teamwork")
        users.toggle_favourite(user, game, skill)
        users.rate(user, game, skill, 4)
        users.delete_account(user)
        assert db.session.scalar(select(func.count(User.id))) == 0
        assert db.session.scalar(select(func.count(Favourite.id))) == 0
        assert db.session.scalar(select(func.count(Rating.id))) == 0


class TestLearningPlan:
    def test_toggle_adds_and_removes(self, user):
        game, skill = get(Game, "coop-kitchen"), get(Skill, "teamwork")
        assert users.toggle_favourite(user, game, skill) is True
        assert users.is_favourite(user, game, skill)
        assert users.toggle_favourite(user, game, skill) is False
        assert not users.is_favourite(user, game, skill)

    def test_plan_is_grouped_by_skill(self, user):
        users.toggle_favourite(user, get(Game, "coop-kitchen"), get(Skill, "teamwork"))
        users.toggle_favourite(user, get(Game, "free-squad"), get(Skill, "teamwork"))
        users.toggle_favourite(user, get(Game, "coop-kitchen"), get(Skill, "communication"))
        plan = users.learning_plan(user)
        assert [s.slug for s in plan] == ["communication", "teamwork"]
        assert len(plan[get(Skill, "teamwork")]) == 2


class TestRatings:
    def test_fr9_one_rating_per_user_game_skill(self, user):
        game, skill = get(Game, "coop-kitchen"), get(Skill, "teamwork")
        users.rate(user, game, skill, 2)
        users.rate(user, game, skill, 5)
        assert db.session.scalar(select(func.count(Rating.id))) == 1
        assert users.user_ratings(user, game) == {skill.id: 5}

    @pytest.mark.parametrize("score", [0, 6, "x"])
    def test_score_must_be_1_to_5(self, user, score):
        with pytest.raises(ValidationError):
            users.rate(user, get(Game, "coop-kitchen"), get(Skill, "teamwork"), score)

    def test_only_listed_skills_can_be_rated(self, user):
        with pytest.raises(ValidationError, match="not listed"):
            users.rate(user, get(Game, "coop-kitchen"), get(Skill, "reaction-time"), 3)
