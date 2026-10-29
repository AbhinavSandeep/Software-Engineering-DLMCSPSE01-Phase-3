"""WTForms definitions. Flask-WTF adds CSRF protection to every form."""

from flask_wtf import FlaskForm
from wtforms import (
    EmailField,
    IntegerField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    URLField,
)
from wtforms.fields.choices import SelectChoice
from wtforms.validators import URL, DataRequired, EqualTo, Length, NumberRange, Optional

from .models import EVIDENCE_LEVELS, PLAY_MODES, PRICE_MODELS, SKILL_CATEGORIES
from .services.filters import PEGI_VALUES

STRENGTH_CHOICES = [SelectChoice("1", "1 weak"), SelectChoice("2", "2 medium"), SelectChoice("3", "3 strong")]


class LoginForm(FlaskForm):
    email = EmailField("E-mail", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    email = EmailField("E-mail", validators=[DataRequired(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm = PasswordField("Repeat password", validators=[DataRequired(), EqualTo("password", "Passwords differ.")])


class SkillForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=80)])
    category = SelectField("Category", choices=[SelectChoice(c, c.capitalize()) for c in SKILL_CATEGORIES])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])


class GameForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=120)])
    genre = StringField("Genre", validators=[DataRequired(), Length(max=40)])
    platforms = StringField("Platforms (separated by ;)", validators=[DataRequired(), Length(max=200)])
    pegi = SelectField("PEGI", choices=[SelectChoice(str(p)) for p in PEGI_VALUES])
    price_model = SelectField("Price model", choices=[SelectChoice(p) for p in PRICE_MODELS])
    play_mode = SelectField("Play mode", choices=[SelectChoice(p) for p in PLAY_MODES])
    session_minutes = IntegerField("Typical session (minutes)", validators=[DataRequired(), NumberRange(1, 600)])
    official_url = URLField("Official page", validators=[DataRequired(), URL()])
    description = TextAreaField("Short description", validators=[Optional(), Length(max=1000)])


class SourceForm(FlaskForm):
    key = StringField("Key", validators=[DataRequired(), Length(max=60)])
    citation = TextAreaField("Citation (APA)", validators=[DataRequired()])
    url = URLField("URL or DOI link", validators=[DataRequired(), URL()])
    evidence = SelectField("Evidence level", choices=[SelectChoice(e) for e in EVIDENCE_LEVELS])


class MappingForm(FlaskForm):
    skill = SelectField("Skill", coerce=int)
    game = SelectField("Game", coerce=int)
    strength = SelectField("Strength", choices=STRENGTH_CHOICES)
    reason = TextAreaField("Reason (one sentence)", validators=[DataRequired(), Length(max=500)])
    sources = SelectMultipleField("Sources", coerce=int)

