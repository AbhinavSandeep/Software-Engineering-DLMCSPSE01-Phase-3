"""Registration, login and logout (FR7)."""

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..forms import LoginForm, RegisterForm
from ..services import ValidationError, users
from . import safe_next

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account.plan"))
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = users.register(form.email.data, form.password.data)
        except ValidationError as exc:
            form.email.errors.append(str(exc))
        else:
            login_user(user)
            flash("Welcome! Your account was created.", "success")
            return redirect(safe_next())
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account.plan"))
    form = LoginForm()
    if form.validate_on_submit():
        user = users.authenticate(form.email.data, form.password.data)
        if user:
            login_user(user)
            flash("You are logged in.", "success")
            return redirect(safe_next())
        # Same message for unknown e-mail and wrong password (no account probing).
        form.password.errors.append("E-mail or password is not correct.")
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You are logged out.", "info")
    return redirect(url_for("catalogue.index"))
