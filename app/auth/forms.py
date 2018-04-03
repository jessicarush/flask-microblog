from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from flask_babel import _, lazy_gettext as _l
from app.models import User


class LoginForm(FlaskForm):
    user_or_email = StringField(_l('Username or email'), validators=[DataRequired()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    remember_me = BooleanField(_l('Remember me'))
    submit = SubmitField(_l('Sign In'))


class ResetPasswordRequestForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    submit = SubmitField(_l('request password reset'))


class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('New Password'), validators=[DataRequired()])
    password2 = PasswordField(_l('Repeat Password'), validators=[DataRequired(),
        EqualTo('password')])
    submit = SubmitField(_l('save this password'))


class RegistrationForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    password2 = PasswordField(_l('Repeat Password'), validators=[DataRequired(),
        EqualTo('password')])
    submit = SubmitField(_l('Register'))

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError(_('That username is taken.'))

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(_('That email is already registered.'))


# The Flask-WTF extension uses Python classes to represent web forms.
# A form class simply defines the fields of the form as class variables.
# The fields that are defined in the LoginForm class know how to render
# themselves as HTML (see app/templates/login.html).

# Email() is another stock validator that comes with WTForms that will ensure
# that what the user types in this field matches the structure of an email
# address. When you add any methods that match the pattern validate_<field>,
# WTForms takes those as custom validators and invokes them in addition to the
# stock validators. In this case we want to make sure that the username and
# email entered by the user are not already in the database. In the event a
# result exists, a validation error is triggered by raising ValidationError.
# The message included as the argument in the exception will be displayed next
# to the field for the user to see
