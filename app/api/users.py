'''
User API routes:

HTTP    Resource URL                  Notes
GET     /api/users/<id> 	          Return a user.
GET 	/api/users 	                  Return the collection of all users.
GET 	/api/users/<id>/followers 	  Return the followers of this user.
GET 	/api/users/<id>/followed 	  Return the users this user is following.
POST 	/api/users 	                  Register a new user account.
PUT 	/api/users/<id> 	          Modify a user.
'''

from flask import jsonify, request, url_for
from app import db
from app.api import bp
from app.api.errors import bad_request
from app.api.tokens import token_auth
from app.models import User


@bp.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
def get_user(id):
    return jsonify(User.query.get_or_404(id).to_dict())
    # get_or_404() returns the object with the given id if it exists, but
    # instead of returning None when the id does not exist, it aborts the
    # request and returns a 404 error to the client. The advantage of
    # get_or_404() over get() is that it removes the need to check the
    # result of the query, simplifying the logic in view functions.


@bp.route('/users', methods=['GET'])
@token_auth.login_required
def get_users():
    data = User.to_collection_dict(User.query)
    return jsonify(data)


@bp.route('/users/<int:id>/followers', methods=['GET'])
@token_auth.login_required
def get_followers(id):
    user = User.query.get_or_404(id)
    data = User.to_collection_dict(user.followers)
    return jsonify(data)


@bp.route('/users/<int:id>/following', methods=['GET'])
@token_auth.login_required
def get_following(id):
    user = User.query.get_or_404(id)
    data = User.to_collection_dict(user.following)
    return jsonify(data)


@bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json() or {}
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return bad_request('must include username, email and password fields')
    if User.query.filter_by(username=data['username']).first():
        return bad_request('that username is already taken')
    if User.query.filter_by(email=data['email']).first():
        return bad_request('that email address is already registered')
    user = User()
    user.from_dict(data, new_user=True)
    db.session.add(user)
    db.session.commit()
    response = jsonify(user.to_dict())
    response.status_code = 201
    # the HTTP protocol requires that a 201 response includes a Location
    # header that is set to the URL of the new resource.
    response.headers['Location'] = url_for('api.get_user', id=user.id)
    return response


@bp.route('/users/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.get_json() or {}
    # to prevent users from changing other users information, we need to
    # check that the token provided matches the user ID provided.
    # The header token includes the word Bearer and a space before the actual
    # token, so we'll remove that before checking.
    token = request.headers.get('Authorization').lstrip('Bearer ')
    if token != user.token:
        return bad_request('The token provided does not match the user id... '
                           'you cannot modify other users data.')
    if 'username' in data and data['username'] != user.username and \
            User.query.filter_by(username=data['username']).first():
        return bad_request('that username is already taken')
    if 'email' in data and data['email'] != user.email and \
            User.query.filter_by(email=data['email']).first():
        return bad_request('that email address is already registered')
    user.from_dict(data, new_user=False)
    db.session.commit()
    return jsonify(user.to_dict())


# @token_auth.login_required
# -----------------------------------------------------------------------------
# If you send a request to any of these endpoints as shown previously, you will
# get back a 401 error response. To gain access, you need to add the
# Authorization header, with a token that you received from a request to
# /api/tokens. Flask-HTTPAuth expects the token to be sent as a "bearer" token,
# which isn't directly supported by HTTPie. For basic authentication with
# username and password, HTTPie offers a --auth option, but for tokens the
# header needs to be explicitly provided. Here is the syntax to send the
# bearer token:

# $ http --auth <username>:<password> POST http://localhost:5000/api/tokens
# $ http GET http://localhost:5000/api/users/1 "Authorization:Bearer <token>"

# Clients can also send a DELETE request to the /tokens URL to invalidate the
# token:

# $ http DELETE http://localhost:5000/api/tokens "Authorization:Bearer <token>"


# zebro.id api request examples
# -----------------------------------------------------------------------------

# get a token:
# $ http --auth soylant:password POST https://zebro.id/api/tokens

# get a user:
# $ http GET https://zebro.id/api/users/1 "Authorization:Bearer <token>"

# get all users:
# $ http GET https://zebro.id/api/users "Authorization:Bearer <token>"

# get followers:
# $ http GET https://zebro.id/api/users/1/followers "Authorization:Bearer <token>"

# get following:
# $ http GET https://zebro.id/api/users/1/following "Authorization:Bearer <token>"

# update user:
# $ http PUT https://zebro.id/api/users/4 "Authorization:Bearer <token>" "about_me=Hello, I am a update."

# revoke token:
# $ http DELETE https://zebro.id/api/tokens "Authorization:Bearer <token>"

# new user:
# $ http POST https://zebro.id/api/users username=test password=password email=test@example.com "about_me=I am a Test!"


# request notes
# -----------------------------------------------------------------------------
# request.headers will return a dictionary like this:

# Host: 127.0.0.1:5000
# User-Agent: HTTPie/0.9.9
# Accept-Encoding: gzip, deflate
# Accept: application/json, */*
# Connection: keep-alive
# Content-Type: application/json
# Authorization: Bearer YNjCBw0I7LCe7nzTk4ydELZgtUILJxlO
# Content-Length: 35
