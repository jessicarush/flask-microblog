'''Basic Authentication Support with tokens.

Provides a way for clients that are not web browsers to log in.'''

from flask import jsonify, g
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from app import db
from app.api import bp
from app.api.errors import error_response
from app.models import User


basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()

@basic_auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return False
    g.current_user = user
    return user.check_password(password)


@token_auth.verify_token
def verify_token(token):
    g.current_user = User.check_token(token) if token else None
    return g.current_user is not None


@basic_auth.error_handler
def basic_auth_error():
    return error_response(401)


@token_auth.error_handler
def token_auth_error():
    return error_response(401)


@bp.route('/tokens', methods=['POST'])
@basic_auth.login_required
def get_token():
    token = g.current_user.get_token()
    db.session.commit()
    return jsonify({'token': token})


@bp.route('/tokens', methods=['DELETE'])
@token_auth.login_required
def revoke_token():
    g.current_user.revoke_token()
    db.session.commit()
    return '', 204



# Flask-HTTPAuth supports a few different authentication mechanisms, all API
# friendly. To begin, I'm going to use HTTP Basic Authentication, in which
# the client sends the user credentials in a standard Authorization HTTP
# Header. To integrate with Flask-HTTPAuth, the application needs to provide
# two functions: one that defines the logic to check the username and password
# provided by the user, and another that returns the error response in the
# case of an authentication failure. These functions are registered with
# Flask-HTTPAuth through decorators, and then are automatically called by the
# extension as needed during the authentication flow.
