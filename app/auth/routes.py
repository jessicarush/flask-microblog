from flask import flash, render_template, redirect, request, url_for
from flask_login import current_user, login_user, logout_user
from flask_babel import _
from werkzeug.urls import url_parse
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordForm, \
    ResetPasswordRequestForm
from app.models import User
from app.auth.email import send_password_reset_email


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('You are registered! Now try signing in.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        # check if field is an existing username:
        user = User.query.filter_by(username=form.user_or_email.data).first()
        # check if field is an existing email:
        if user is None:
            user = User.query.filter_by(email=form.user_or_email.data).first()
        # if not found by username or email:
        if user is None:
            flash(_("Can't find that username or email."))
            return redirect(url_for('auth.login'))
        # if the username is good but password fails:
        if user and not user.check_password(form.password.data):
            flash(_('Incorrect password.'))
            return redirect(url_for('auth.login'))
        # otherwise, all is well:
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash(_('Check your email for the link to reset your password.'))
        # The flashed message is displayed even if the email provided by the
        # user is unknown. This is so that clients cannot use this form to
        # figure out if a given user is a member or not.
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


# login(), @login_required: see notes in app/main/routes.py
