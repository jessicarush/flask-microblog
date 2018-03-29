from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length, Email
from flask_babel import _, lazy_gettext as _l
from app.models import User


class SearchForm(FlaskForm):
    q = StringField(_l('Search'), validators=[DataRequired()])
    # For a form that has a text field, the browser will submit the form when
    # you press Enter with the focus on the field, so a button is not needed.

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)


class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    about_me = TextAreaField(_l('About me'), validators=[Length(min=0, max=350)])
    submit = SubmitField(_l('Submit'))

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError(_('That username is taken.'))

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=self.email.data).first()
            if user is not None:
                raise ValidationError(_('That email is already registered.'))


class PostForm(FlaskForm):
    post = TextAreaField(_l('Say something'), validators=[DataRequired(),
        Length(min=1, max=280)])
    submit = SubmitField(_l('Post'))


# In the EditProfileForm, the three methods are in place to prevent the bug
# where someone could change their username or email to one that is already
# in the database and cause a server error. This is not a perfect solution,
# because it may not work when two or more processes are accessing the database
# at the same time. In that situation, a race condition could cause the
# validation to pass, but a moment later when the rename is attempted the
# database was already changed by another process and cannot rename the user.
# This is somewhat unlikely except for very busy applications that have a lot
# of server processes.

# In the SearchForm, the __init__ constructor provides values for the formdata
# and csrf_enabled arguments if they are not provided by the caller. The
# formdata argument determines from where Flask-WTF gets form submissions.
# The default is to use request.form, which is where Flask puts form values
# that are submitted via POST request. Forms that are submitted via GET request
# get the field values from the query string, so we need to point Flask-WTF at
# request.args, which is where Flask writes the query string arguments. Forms
# have CSRF protection added by default, with the inclusion of a CSRF token
# that is added to the form via the form.hidden_tag() construct in templates.
# For clickable search links to work, CSRF needs to be disabled, so we set
# csrf_enabled to False so that Flask-WTF knows that it needs to bypass CSRF
# validation for this form.
