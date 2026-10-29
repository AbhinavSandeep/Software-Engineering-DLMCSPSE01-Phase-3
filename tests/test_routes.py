"""Integration tests: Flask routes together with the test database."""

from sqlalchemy import func, select

from app import create_app
from app.extensions import db
from app.models import Game, Rating, Skill


def ids(game_slug, skill_slug):
    game = db.session.scalar(select(Game).where(Game.slug == game_slug))
    skill = db.session.scalar(select(Skill).where(Skill.slug == skill_slug))
    return game, skill


class TestPublicPages:
    def test_index_lists_skills_by_category(self, client):
        page = client.get("/").get_data(as_text=True)
        assert "Teamwork" in page and "social skills" in page

    def test_fr2_acceptance_results_sorted_by_score(self, client):
        page = client.get("/recommend?skill=teamwork&skill=communication").get_data(as_text=True)
        assert page.index("Coop Kitchen") < page.index("Free Squad") < page.index("Puzzle Box")
        assert "Score 3.5" in page

    def test_fr3_results_show_reason_evidence_and_source(self, client):
        page = client.get("/recommend?skill=teamwork").get_data(as_text=True)
        assert "Needs coordination." in page and "Evidence B" in page and "https://example.org/b" in page

    def test_fr4_acceptance_filters_and_reset(self, client):
        page = client.get("/recommend?skill=teamwork&pegi_max=12&price_model=free").get_data(as_text=True)
        assert "Puzzle Box" in page and "Free Squad" not in page and "Coop Kitchen" not in page
        assert "Reset filters" in page

    def test_no_skill_redirects_with_message(self, client):
        response = client.get("/recommend", follow_redirects=True)
        assert "at least one skill" in response.get_data(as_text=True)

    def test_too_many_skills_are_refused(self, client):
        url = "/recommend?skill=teamwork&skill=communication&skill=problem-solving&skill=reaction-time"
        assert "at most 3" in client.get(url, follow_redirects=True).get_data(as_text=True)

    def test_fr5_game_detail(self, client):
        page = client.get("/games/free-squad").get_data(as_text=True)
        assert "Reaction time" in page and "Teamwork" in page and "Forum C (2022)." in page

    def test_unknown_game_is_404(self, client):
        assert client.get("/games/nope").status_code == 404

    def test_fr6_search(self, client):
        page = client.get("/search?q=squad").get_data(as_text=True)
        assert "Free Squad" in page and "Reaction time" in page

    def test_how_it_works(self, client):
        assert "strength × evidence weight" in client.get("/how-it-works").get_data(as_text=True)


class TestAccountFlow:
    def test_register_logs_in(self, client):
        response = client.post("/register", data={"email": "new@example.org", "password": "long-password",
                                                  "confirm": "long-password"}, follow_redirects=True)
        assert "account was created" in response.get_data(as_text=True)

    def test_wrong_password_shows_neutral_message(self, client, user):
        page = client.post("/login", data={"email": "lena@example.org", "password": "x"}).get_data(as_text=True)
        assert "E-mail or password is not correct." in page

    def test_plan_requires_login(self, client):
        assert client.get("/plan").status_code == 302

    def test_fr8_save_and_print_plan(self, user_client):
        game, skill = ids("coop-kitchen", "teamwork")
        user_client.post("/plan/toggle", data={"game_id": game.id, "skill_id": skill.id, "next": "/plan"})
        assert "Coop Kitchen" in user_client.get("/plan").get_data(as_text=True)
        assert "Needs coordination." in user_client.get("/plan/print").get_data(as_text=True)

    def test_open_redirect_is_blocked(self, user_client):
        game, skill = ids("coop-kitchen", "teamwork")
        response = user_client.post("/plan/toggle", data={"game_id": game.id, "skill_id": skill.id,
                                                          "next": "https://evil.example.com"})
        assert response.headers["Location"].endswith("/plan")

    def test_fr9_rate_game(self, user_client):
        game, skill = ids("coop-kitchen", "teamwork")
        response = user_client.post("/rate", data={"game_id": game.id, "skill_id": skill.id, "score": "4"},
                                    follow_redirects=True)
        assert "rating for Teamwork was saved" in response.get_data(as_text=True)
        assert db.session.scalar(select(func.count(Rating.id))) == 1

    def test_delete_account_needs_confirmation(self, user_client):
        assert "Type DELETE" in user_client.post("/account/delete", data={"confirm": "no"},
                                                 follow_redirects=True).get_data(as_text=True)
        page = user_client.post("/account/delete", data={"confirm": "DELETE"}, follow_redirects=True)
        assert "were deleted" in page.get_data(as_text=True)

    def test_logout(self, user_client):
        assert "logged out" in user_client.post("/logout", follow_redirects=True).get_data(as_text=True)


class TestAdmin:
    def test_normal_user_gets_403(self, user_client):
        assert user_client.get("/admin/").status_code == 403

    def test_dashboard(self, admin_client):
        assert "Coop Kitchen" in admin_client.get("/admin/").get_data(as_text=True)

    def test_fr10_create_and_delete_skill(self, admin_client):
        admin_client.post("/admin/skills/new", data={"name": "Creativity", "category": "cognitive", "description": ""})
        skill = db.session.scalar(select(Skill).where(Skill.slug == "creativity"))
        assert skill is not None
        admin_client.post(f"/admin/skill/{skill.id}/delete")
        assert db.session.scalar(select(Skill).where(Skill.slug == "creativity")) is None

    def test_create_game(self, admin_client):
        admin_client.post("/admin/games/new", data={
            "title": "Admin Game", "genre": "Puzzle", "platforms": "PC", "pegi": "3", "price_model": "free",
            "play_mode": "single", "session_minutes": "10", "official_url": "https://example.org/x"})
        assert db.session.scalar(select(Game).where(Game.slug == "admin-game")) is not None

    def test_edit_forms_render(self, admin_client):
        game, skill = ids("coop-kitchen", "teamwork")
        for url in (f"/admin/games/{game.id}", f"/admin/skills/{skill.id}", f"/admin/mappings/{game.mappings[0].id}",
                    "/admin/sources/1", "/admin/mappings/new"):
            assert admin_client.get(url).status_code == 200

    def test_mapping_without_source_is_refused(self, admin_client):
        game, skill = ids("puzzle-box", "communication")
        page = admin_client.post("/admin/mappings/new", data={"skill": skill.id, "game": game.id, "strength": "2",
                                                              "reason": "Talk."}).get_data(as_text=True)
        assert "at least one source" in page


class TestApi:
    def test_health(self, client):
        assert client.get("/api/health").get_json() == {"status": "ok"}

    def test_recommendations(self, client):
        data = client.get("/api/recommendations?skill=teamwork").get_json()
        assert data[0]["slug"] == "coop-kitchen" and data[0]["sources"]

    def test_bad_request(self, client):
        assert client.get("/api/recommendations").status_code == 400


def test_csrf_protects_forms():
    """With CSRF enabled (as in production), a POST without token is rejected."""
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        db.create_all()
        assert app.test_client().post("/login", data={"email": "a@b.org", "password": "x"}).status_code == 400
        db.drop_all()
