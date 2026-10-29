"""Unit tests of the recommendation service (FR2, FR3)."""

from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models import Game, Skill
from app.services import ValidationError, users
from app.services.filters import GameFilter
from app.services.recommendation import normalise_rating, recommend, resolve_skills, score_game


def mapping(strength, evidence):
    return SimpleNamespace(strength=strength, best_evidence=evidence)


def skills(*slugs):
    return resolve_skills(list(slugs))


class TestScoreFormula:
    def test_phase1_example_scores_3_5(self):
        assert score_game([mapping(3, "B"), mapping(2, "B")], None, 0) == 3.5

    def test_evidence_weights(self):
        assert score_game([mapping(1, "A")], None, 0) == 1.0
        assert score_game([mapping(1, "B")], None, 0) == 0.7
        assert score_game([mapping(1, "C")], None, 0) == 0.4

    def test_ratings_ignored_below_minimum(self):
        assert score_game([mapping(2, "A")], 5.0, 2) == 2.0

    def test_ratings_used_from_minimum(self):
        assert score_game([mapping(2, "A")], 5.0, 3) == 2.5
        assert score_game([mapping(2, "A")], 1.0, 3) == 1.5

    def test_normalise_rating_range(self):
        assert normalise_rating(1) == -1
        assert normalise_rating(3) == 0
        assert normalise_rating(5) == 1


class TestResolveSkills:
    def test_keeps_selection_order(self, app):
        assert [s.slug for s in skills("communication", "teamwork")] == ["communication", "teamwork"]

    def test_requires_one_skill(self, app):
        with pytest.raises(ValidationError):
            resolve_skills([])

    def test_rejects_more_than_three(self, app):
        with pytest.raises(ValidationError, match="at most 3"):
            resolve_skills(["teamwork", "communication", "problem-solving", "reaction-time"])

    def test_rejects_unknown_skill(self, app):
        with pytest.raises(ValidationError):
            resolve_skills(["juggling"])

    def test_duplicates_are_merged(self, app):
        assert len(resolve_skills(["teamwork", "teamwork"])) == 1


class TestRecommend:
    def test_fr2_only_matching_games_sorted_by_score(self, app):
        results = recommend(skills("teamwork", "communication"))
        assert [r.game.slug for r in results] == ["coop-kitchen", "free-squad", "puzzle-box"]
        assert [r.score for r in results] == [3.5, 2.0, 0.4]

    def test_game_without_selected_skill_is_not_listed(self, app):
        results = recommend(skills("problem-solving"))
        assert [r.game.slug for r in results] == ["puzzle-box"]

    def test_fr3_every_result_has_reason_evidence_and_source(self, app):
        for r in recommend(skills("teamwork")):
            assert r.mappings and all(m.reason for m in r.mappings)
            assert r.best_evidence in "ABC"
            assert r.source_count >= 1

    def test_filter_is_applied(self, app):
        results = recommend(skills("teamwork"), GameFilter(price_model="free"))
        assert {r.game.slug for r in results} == {"free-squad", "puzzle-box"}

    def test_tie_broken_by_number_of_sources(self, app):
        # Give Puzzle Box a teamwork score equal to Free Squad's, but with fewer sources.
        game = db.session.scalar(db.select(Game).where(Game.slug == "free-squad"))
        game.mappings[0].strength = 1
        db.session.commit()
        results = recommend(skills("reaction-time", "teamwork"))
        assert results[0].game.slug == "free-squad"

    def test_ratings_change_the_ranking(self, app):
        team = db.session.scalar(db.select(Skill).where(Skill.slug == "teamwork"))
        squad = db.session.scalar(db.select(Game).where(Game.slug == "free-squad"))
        for i in range(3):
            users.rate(users.register(f"u{i}@example.org", "password-123"), squad, team, 5)
        result = next(r for r in recommend([team]) if r.game.slug == "free-squad")
        assert result.rating_count == 3
        assert result.score == 2.5
