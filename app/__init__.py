"""XPtoIRL application factory."""

import os

import click
from flask import Flask, render_template

from .config import CONFIGS
from .extensions import csrf, db, login_manager, migrate

__version__ = "1.0.0"


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    config_name = config_name or os.environ.get("APP_ENV", "development")
    app.config.from_object(CONFIGS[config_name])

    if config_name == "production" and app.config["SECRET_KEY"] == "dev-only-change-me":
        raise RuntimeError("SECRET_KEY must be set in production.")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401  (register models with SQLAlchemy)
    from .controllers import account, admin, api, auth, catalogue, games, recommend

    for blueprint in (catalogue.bp, recommend.bp, games.bp, auth.bp, account.bp, admin.bp, api.bp):
        app.register_blueprint(blueprint)
    csrf.exempt(api.bp)  # read-only JSON endpoints

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    @app.context_processor
    def inject_globals():
        return {"app_version": __version__}

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    _register_cli(app)
    return app


def _register_cli(app: Flask) -> None:
    from . import models
    from .services import ValidationError, importer, users

    @app.cli.command("seed")
    @click.option("--data-dir", default=None, help="Folder with the four CSV files.")
    @click.option("--if-empty", is_flag=True, help="Only import when the database has no skills yet.")
    def seed(data_dir, if_empty):
        """Create missing tables and import the curated CSV data set."""
        db.create_all()
        if if_empty and db.session.scalar(db.select(db.func.count(models.Skill.id))):
            click.echo("Data already present, import skipped.")
            return
        try:
            report = importer.import_directory(data_dir or app.config["DATA_DIR"])
        except ValidationError as exc:
            raise click.ClickException(str(exc)) from None
        click.echo(f"Import finished: {report.summary()}")

    @app.cli.command("create-admin")
    @click.argument("email")
    @click.password_option(envvar="ADMIN_PASSWORD")
    def create_admin(email, password):
        """Create an administrator account (password from prompt or ADMIN_PASSWORD)."""
        try:
            user = users.register(email, password, role="admin")
        except ValidationError as exc:
            raise click.ClickException(str(exc)) from None
        click.echo(f"Administrator {user.email} created.")
