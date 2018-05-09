import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from config import Config
from elasticsearch import Elasticsearch
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_moment import Moment
from flask_babel import Babel, lazy_gettext as _l
from redis import Redis
import rq


db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access that page.')
mail = Mail()
moment = Moment()
babel = Babel()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('microblog-tasks', connection=app.redis)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    babel.init_app(app)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    if not app.debug and not app.testing:
        # email error logs:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='Microblog Failure',
                credentials=auth, secure=secure)
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        # file error logs:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Microblog startup')

    return app


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])


from app import models


# Flask-Migrate
# -----------------------------------------------------------------------------
# Flask-Migrate is a wrapper for Alembic, a database migration framework for
# SQLAlchemy. Working with database migrations adds a bit of work to get a
# database started, but that is a small price to pay for the flexibility to
# make changes to your database in the future. Alembic maintains a migration
# repository, which is a directory in which it stores its migration scripts.
# Each time a change is made to the database schema, a migration script is
# added to the repository with the details of the change. To apply the
# migrations to a database, these scripts are executed in the sequence they
# were created. To create the migration repository run:

# (venv) $ flask db init

# The flask command relies on the FLASK_APP environment variable to know where
# the Flask application lives ($ export FLASK_APP=microblog.py).

# With the migration repository in place, create the first database migration,
# which will include the table that maps to the User database model.
# There are two ways to create a database migration: manually or automatically.
# To generate a migration automatically, Alembic compares the database schema
# as defined by the models, against the actual database schema currently used
# in the database. It then populates the migration script with the changes
# necessary to make the database schema match the application models. In this
# case, since there is no previous database, the automatic migration will add
# the entire User model to the migration script:

# (venv) $ flask db migrate -m "users table"

# The migration script has two functions called upgrade() and downgrade().
# The upgrade() function applies the migration, and the downgrade() function
# removes it. The flask db migrate command does not make any changes to the
# database, it just generates the migration script. To apply the changes to
# the database, the flask db upgrade command must be used:

# (venv) $ flask db upgrade

# With SQLite, the upgrade command create a database if it doesn't exist.
# When using MySQL or PostgreSQL, you have to create the database in the
# database server before running upgrade function.

# In terms of managing your development app and production server app, anytime
# you make changes to your models (schema), you generate a new migration
# script (flask db migrate), review it and then apply it to your database
# (flask db upgrade). When you're ready to release it to your production server,
# you would commit, pull everything to the server, then run (flask db upgrade).
# If ever you make a mistake, you can (flask db downgrade), delete the
# migration script, and then generate a new one.


# Flask-Login
# -----------------------------------------------------------------------------
# This extension manages the user logged-in state, so that users can log in to
# the application and then navigate to different pages while the application
# "remembers" that the user is logged in. It also provides the "remember me"
# functionality that allows users to remain logged in even after closing the
# browser window. See models.py

# Requiring Users To Login

# Flask-Login provides a very useful feature that forces users to log in before
# they can view certain pages of the application. If a user who is not logged
# in tries to view a protected page, Flask-Login will automatically redirect
# the user to the login form, and only redirect back to the page the user
# wanted to view after the login process is complete. For this feature to be
# implemented, Flask-Login needs to know what is the view function that handles
# logins: login.login_view = 'login'

# The way Flask-Login protects a view function against anonymous users is with
# a decorator called @login_required. When you add this decorator to a view
# function below the @app.route decorators from Flask, the function becomes
# protected and will not allow access to users that are not authenticated.


# Logging to Email
# -----------------------------------------------------------------------------
# Flask uses Python's logging package to write its logs, and this package
# already has the ability to send logs by email. All we need to do to is to add
# a SMTPHandler instance to the Flask logger object, which is app.logger.
# We only enable the email logger when the application is running without
# debug mode, which is indicated by app.debug being True, and also when the
# email server exists in the configuration. Setting up the email logger is
# somewhat tedious due to having to handle optional security options that are
# present in many email servers. But in essence, the code above creates a
# SMTPHandler instance, sets its level so that it only reports errors and not
# warnings, informational or debugging messages, and finally attaches it to
# the app.logger object from Flask


# Logging to File
# -----------------------------------------------------------------------------
# The above will write a log file named microblog.log in a logs directory. The
# RotatingFileHandler class is nice because it rotates the logs, ensuring that
# the log files do not grow too large when the application runs for a long time.
# In this case we're limiting the size of the log file to 10KB, and keeping the
# last ten log files as backup.

# The logging.Formatter class provides custom formatting for the log messages.
# Since these messages are going to a file, we want them to have as much
# information as possible. So the above includes the timestamp, the logging
# level, the message and the source file and line number from where the log
# entry originated. To make the logging more useful, we also lowered the logging
# level to the INFO category, both in the application logger and the file
# logger handler. The logging categories are DEBUG, INFO, WARNING, ERROR and
# CRITICAL in increasing order of severity.


# Flask-Moment
# -----------------------------------------------------------------------------
# A reminder: it's best to avoid working with timezones. Instead, do all
# your processing in UTC and then convert to timezones at the end for the user.
# As it turns out, the web browser knows the user's timezone, and exposes it
# through the standard date and time JavaScript APIs. A good way of utilizing
# this is to let the conversion from UTC to a local timezone happen in the
# web client using JavaScript.

# Moment.js is a small open-source JavaScript library does this. It provides
# every imaginable formatting option, and then some. Flask-Moment, a small
# Flask extension that makes it easy to incorporate moment.js into your app.

# Since Flask-Moment works together with moment.js, all templates of the
# application must include this library. The best way is to add it to the head
# section of the base template using:

# {{ moment.include_jquery() }}
# {{ moment.include_moment() }}

# Then in the template where we had something like:
# {{ user.last_seen }}

# We change to:
# {{ moment(user.last_seen).format('LL') }}

# for more fomrmats see: https://momentjs.com/

# Keep in mind, by default moment.js is meant to be passed an ISO 8601
# format string. The Flask-Moment extension makes it so that we can pass
# datetime objects instead.


# Flask-babel
# -----------------------------------------------------------------------------
# This extension is used for language translation. Note this is referred to as
# Internationalization and Localization, commonly abbreviated I18n and L10n.
# To keep track of the languages, we've created a variable in config.py. You
# can use standard two-letter language codes or, a country code can be added
# as well. For example, you could use en-US, en-GB and en-CA to support
# American, British and Canadian English as different languages.

# https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes

# The Babel instance provides a localeselector decorator. The decorated
# function is invoked for each request to select a language translation to
# use for that request:


# get_locale()
# -----------------------------------------------------------------------------
# We're using an attribute of Flask's request object called accept_languages.
# This object works with the Accept-Language header that clients send with a
# request. This header specifies the client language and locale preferences as
# a weighted list which can be configured in the browser's preferences page.
# The default is usually imported from the language settings in the OS. Most
# people don't even know such a setting exists, but can be useful as users can
# provide a list of preferred languages, each with a weight. Here is an example
# of a complex Accept-Languages header:

# Accept-Language: da, en-gb;q=0.8, en;q=0.7


# Marking text to translate in python source code
# -----------------------------------------------------------------------------
# Note: this part is tedious and adds some very weird syntax to your code, but
# apparently there's no way around it. Each piece of text, no matter where or
# how its generated, needs to be wrapped with flask_babel's _() function.

# from flask_babel import _

# flash('Your post is now live!')
# flash(_('Your post is now live!'))

# When using variables, you have to use old style formatting:
# flash('User {} not found.'.format(username))
# flash(_('User %(username)s not found.', username=username))

# Some string literals are assigned outside of a request, usually when the
# application is starting up (ie forms). For these we use a different function.

# from flask_babel import lazy_gettext as _l

# class LoginForm(FlaskForm):
#     username = StringField(_l('Username'), validators=[DataRequired()])


# Marking text to translate in jinja templates
# -----------------------------------------------------------------------------
# <h1>Hello</h1>
# <h1>{{ _('Hello') }}</h1>

# <p>Hello {{ current_user.username }} </p>
# <p>{{ _('Hello, %(username)s', username=current_user.username) }}</p>

# A difficult situation:

# <a href="{{ url_for('user', username=post.author.username) }}">
#     {{ post.author.username }} </a>
# said {{ moment(post.timestamp).fromNow() }}:

# The solution uses an intermediate variable called user_link using the set
# and endset template directives, and then pass that as an argument to the
# translation function.

# {% set user_link %}
#     <a href="{{ url_for('user', username=post.author.username) }}">
#         {{ post.author.username }}</a>
# {% endset %}
# {{ _('%(username)s said %(when)s', username=user_link, when=moment(post.timestamp).fromNow()) }}

# But this should work too:

# <a href="{{ url_for('user', username=post.author.username) }}">
#     {{ _('%(username)s'), username=post.author.username }} </a>
# said {{ _('%(when)s'), when=moment(post.timestamp).fromNow() }}:


# Extracting text to translate
# -----------------------------------------------------------------------------
# Once you have all the _() and _l() in place, you can use the pybabel command
# to extract them to a .pot file (portable object template). This is a text
# file that includes all the texts that were marked as needing translation.
# The purpose of this file is to serve as a template to create translation
# files for each language. The extraction process needs a small configuration
# file that tells pybabel what files should be scanned for translatable texts.
# See babel.cfg. The first two lines define the filename patterns for Python
# and Jinja2 template files respectively. The third line defines two extensions
# provided by the Jinja2 template engine that help Flask-Babel properly parse
# template files. To extract all the texts to the .pot file:

# (venv) $ pybabel extract -F babel.cfg -k _l -o messages.pot .

# The pybabel extract command reads the configuration file given in the -F
# option, then scans all the code and template files in the directories that
# match the configured sources, starting from the directory given in the
# command (the current directory or . in this case). By default, pybabel will
# look for _() as a text marker, but I have also used the lazy version, which
# I imported as _l(), so I need to tell the tool to look for those too with the
# -k _l. The -o option provides the name of the output file.


# Generating a language catalogue
# -----------------------------------------------------------------------------
# The next step in the process is to create a translation for each additional
# language that will be supported:

# (venv) $ pybabel init -i messages.pot -d app/translations -l es creating catalog app/translations/es/LC_MESSAGES/messages.po based on messages.pot

# The pybabel init command takes the messages.pot file as input and writes a
# new language catalog to the directory given in the -d option for the language
# specified in the -l option. I'm going to be installing all the translations
# in the app/translations directory, because that is where Flask-Babel will
# expect translation files to be by default. The command will create a es
# subdirectory inside this directory for the Spanish data files. In particular,
# there will be a new file named app/translations/es/LC_MESSAGES/messages.po,
# that is where the translations need to be made. If you want to support other
# languages, just repeat the above command with each of the language codes you
# want, so that each language gets its own repository with a messages.po file.

# There are many translation applications that work with .po files. If you
# feel comfortable editing the text file, that's great, but if you are working
# with a large project it may be recommended to work with a specialized editor.
# The most popular translation application is the open-source poedit:
# https://poedit.net/

# If you are familiar with vim, then the po.vim plugin gives some key mappings
# that make working with these files easier.

# To be clear, you have to actually type/paste your own translations in here!

# The messages.po file is a sort of source file for translations. When you
# want to start using these translated texts, this file needs to be compiled
# into a format that is efficient to be used by the application at run-time:

# (venv) $ pybabel compile -d app/translations

# This operation adds a messages.mo file next to messages.po in each language
# repository. The .mo file is the file that Flask-Babel will use to load
# translations for the application.


# Updating translations
# -----------------------------------------------------------------------------
# One common situation when working with translations is that you may want to
# start using a translation file even if it is incomplete. That is totally fine,
# you can compile an incomplete messages.po file and any translations that are
# available will be used, while any missing ones will use the base language.
# You can then continue working on the translations and compile again to update
# the messages.mo file as you make progress. Another common scenario occurs if
# you missed some texts when you added the _() wrappers.

# When you're ready to update:

# (venv) $ pybabel extract -F babel.cfg -k _l -o messages.pot .
# (venv) $ pybabel update -i messages.pot -d app/translations

# The update call takes the new messages.pot file and merges it into all the
# messages.po files associated with the project. This is going to be an
# intelligent merge, in which any existing texts will be left alone, while only
# entries that were added or removed in messages.pot will be affected.

# After the messages.po are updated, you can go ahead and translate any new
# texts, then compile the messages one more time to make them available to the
# application:

# (venv) $ pybabel compile -d app/translations


# Translating dates & times
# -----------------------------------------------------------------------------
# Since the timestamps are generated by Flask-Moment and moment.js, they are
# not included in the translation effort because none of the text generated by
# these packages are part of the source code or templates of the application.

# The moment.js library does support localization and internationalization, so
# all we need to do is configure the proper language. Flask-Babel returns the
# selected language and locale for a given request via get_locale(), so what
# we do is add the locale to flasks g object, so that we can then access it
# from the base template.

# In routes.py add to before_request():
# g.locale = str(get_locale())

# In base.html head sections add:
# {{ moment.lang(g.locale) }}


# Ajax
# -----------------------------------------------------------------------------
# We are going to implement live, automated translations of user posts as an
# Ajax service. This requires a few steps. First, we need a way to identify the
# source language of the text to translate. We also need to know the preferred
# language for each user, because we want to show a "translate" link only for
# posts written in other languages. When a translation link is offered and the
# user clicks on it, we need to send the Ajax request to the server, and the
# server will contact a third-party translation API. Once the server sends back
# a response with the translated text, the client-side javascript code will
# dynamically insert this text into the page.

# In Python, there is a good language detection library called guess_language.

# (venv) $ pip install guess-language_spirit

# The plan is to feed each blog post to this package, to try to determine the
# language. Since doing this analysis is somewhat time consuming, I don't want
# to repeating this work every time a post is rendered to a page. What I'm
# going to do is set the source language for a post at the time it's submitted.
# The detected language is then going to be stored in the posts table.


# Creating a flask blueprint
# -----------------------------------------------------------------------------
# In Flask, a blueprint is a logical structure that represents a subset of
# the application. A blueprint can include elements such as routes, view
# functions, forms, templates and static files. If you write your blueprint
# in a separate Python package, then you have a component that encapsulates
# the elements related to specific feature of the application.

# The contents of a blueprint are initially in a dormant state. To associate
# these elements, the blueprint needs to be registered with the application.
# During the registration, all the elements that were added to the blueprint
# are passed on to the application. Think of a blueprint as a temporary storage
# for application functionality that helps in organizing your code.

# The Blueprint class takes the name of the blueprint, the name of the base
# module (typically set to __name__ like in the Flask application instance),
# and a few optional arguments. After the blueprint object is created, we
# import the handlers.py module, so that the error handlers are registered
# with the blueprint. The import at the bottom avoids circular dependencies.

# see the init file in errors, auth, main


# Moving html templates to other directories
# -----------------------------------------------------------------------------
# Flask blueprints can be configured to have a separate directory for templates
# or static files. We have decided to move templates into sub-directories of
# in application's template directory so that all templates are in a single
# spot, but if you prefer to have the templates that belong to a blueprint
# inside the blueprint's package, add a template_folder='templates' argument
# to the Blueprint() constructor, you can then store this blueprint's templates
# in app/errors/templates instead of app/templates/errors.


# Registering Blueprints
# -----------------------------------------------------------------------------
# To register a blueprint, the register_blueprint() method of the Flask
# application instance is used. When a blueprint is registered, any view
# functions, templates, static files, error handlers, etc. are connected to the
# application. We put the import of the blueprint right above the
# app.register_blueprint() to avoid circular dependencies.

# The register_blueprint() call for the auth_bp has an extra argument,
# url_prefix. This is entirely optional. Flask gives you the option to attach
# a blueprint under a URL prefix, so any routes defined in the blueprint get
# this prefix in their URLs. In many cases this is useful as a sort of
# "namespacing" that keeps all the routes in the blueprint separated from other
# routes in the application or other blueprints. For authentication, I thought
# it was nice to have all the routes starting with /auth, so I added the prefix.
# So now the login URL is going to be http://localhost:5000/auth/login.
# Because I'm using url_for() to generate the URLs, all URLs will automatically
# incorporate the prefix.


# The "Application Factory Pattern": create_app()
# -----------------------------------------------------------------------------
# Having the application as a global variable introduces some complications,
# mainly in the form of limitations for some testing scenarios. Before we
# introduced blueprints, the application had to be a global variable, because
# all the view functions and error handlers needed to be decorated with
# decorators that come from app, such as @app.route. But now all routes and
# error handlers were moved to blueprints, there are a lot less reasons to keep
# the application global. So what we do, is add a function called create_app()
# that constructs a Flask application instance, and eliminate the global
# variable.

# We have seen that most Flask extensions are initialized by creating an
# instance of the extension and passing the application as an argument. When
# the application does not exist as a global variable, there is an alternative
# mode in which extensions are initialized in two phases. The extension
# instance is first created in the global scope as before, but no arguments
# are passed to it. This creates an instance of the extension that is not
# attached to the application. At the time the application instance is created
# in the factory function, the init_app() method must be invoked on the
# extension instances to bind it to the now known application.

# Most references to app went away with the introduction of blueprints,
# (@bp.route instead of app.route) but we with our new application factory
# function, we'll also have to modify all references to app.config and their
# related imports (from app import app) since app is now inside the factory
# function. Flask tries to make this easy. The current_app variable that
# Flask provides (from flask import current_app) is a special "context"
# variable that Flask initializes with the application before it dispatches
# a request. We have seen context variables before: the g variable in which
# we're storing the current locale and Flask-Login's current_user. These are
# somewhat "magical" variables, in that they work like global variables, but
# are only accessible during the handling of a request, and only in the thread
# that is handling it. Replacing 'app' with Flask's 'current_app' variable
# eliminates the need of importing the application instance as a global
# variable. Once we change all our 'from app import app' to
# 'from flask import current_app', we can update all references to app.config
# with current_app.config.


# Elasticsearch
# -----------------------------------------------------------------------------
# Make sure it's running: cd to the directory where it lives then launch by
# typing 'elasticsearch'. To stop elasticsearch, ctrl-c.

# sudo cd /usr/local/bin/
# elasticsearch

# Check that it's running here: http://localhost:9200/

# In order to keep the search functionality as generic as possible (so that
# it can extend to other models), we create an 'abstraction'. Any model that
# contains fields that we want to be indexed, we define a class attribute
# called __searchable__. This attribute is just a variable, and does not have
# any behavior associated with it. In this application, we'll only need to add
# it to the Posts model.


# Circular imports
# -----------------------------------------------------------------------------
# The bottom import is a workaround to circular imports, a common problem with
# Flask applications. The routes module needs to import the app variable
# defined in this script, so putting one of the reciprocal imports at the
# bottom avoids the error that results from the mutual references between these
# two files.
