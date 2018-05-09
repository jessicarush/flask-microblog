import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'password'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    POSTS_PER_PAGE = 25
    LANGUAGES = ['en', 'es', 'fr']
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'

    # For emailing error log:
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['jesskrush@me.com']


# Flask (and possibly some Flask extensions you use) offer some amount of
# freedom in how to do things. You can pass preferences to the framework
# as a list of configuration variables.

# There are several formats for the application to specify configuration
# options. The most basic solution is to define your variables as keys in
# app.config, which uses a dictionary style to work with variables:

# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'fancypassword'
# ... add more variables here as needed

# That being said, to enforce the principle of separation of concerns, instead
# of putting the configuration in the same place as where we create the
# application, you can use this structure that allows you to keep the
# configuration in a separate file. As the application needs more configuration
# items, they can be added to the class above.

# The SECRET_KEY configuration variable is an important part in most Flask apps.
# Flask and some of its extensions use the value of the secret key as a
# cryptographic key, useful to generate signatures or tokens. The Flask-WTF
# extension uses it to protect web forms against a nasty attack called
# Cross-Site Request Forgery or CSRF.

# The idea is that a value sourced from an environment variable is preferred,
# but if the environment does not define the variable, then the hardcoded
# string is used instead. When you are developing an app, the security
# requirements are low, so you can just ignore this setting and let the
# hardcoded string be used. But when the app is deployed on a production server,
# set a unique and difficult to guess value in the environment, so that the
# server has a secure key that nobody else knows. #TODO


# Environmental Variables
# -----------------------------------------------------------------------------
# see all current:

# (venv) $ printenv

# flask:

# (venv) $ export FLASK_APP=microblog.py
# (venv) $ flask shell
# (venv) $ flask run

# database:

# (venv) $ export DATABASE_URL=postgresql://username:password@host/database_name
# (venv) $ export DATABASE_URL=postgresql://postgres:password@localhost/exercise_app

# Microsoft azure translation api key:

# (venv) $ export MS_TRANSLATOR_KEY=e0900c3683cf4ec1aa604c271058d7b9

# gmail:

# (venv) $ export MAIL_SERVER=smtp.googlemail.com
# (venv) $ export MAIL_PORT=587
# (venv) $ export MAIL_USE_TLS=1
# (venv) $ export MAIL_USERNAME=<your-gmail-username>
# (venv) $ export MAIL_PASSWORD=<your-gmail-password>

# The configuration variables for email include the server and port, a boolean
# flag to enable encrypted connections, and optional username and password. The
# five configuration variables are sourced from their environment variable
# counterparts. If the email server is not set in the environment, then we use
# that as a sign that emailing errors needs to be disabled. The email server
# port can also be given in an environment variable, but if not set, the
# standard port 25 is used. Email server credentials are by default not used,
# but can be provided if needed. The ADMINS configuration variable is a list of
# the email addresses that will receive error reports.

# To test sending an email, try this in the flask shell:

# >>> from flask_mail import Message
# >>> from app import mail
# >>> msg = Message('test subject', sender=app.config['ADMINS'][0],
#     recipients=['jesskrush@me.com', 'hello@cyan.red'])
# >>> msg.body = 'text body'
# >>> msg.html = '<h1>HTML body</h1>'
# >>> mail.send(msg)
