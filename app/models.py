from datetime import datetime
from hashlib import md5
from time import time
from flask import current_app
from flask_login import UserMixin
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from app.search import add_to_index, remove_from_index, query_index


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': [obj for obj in session.new if isinstance(obj, cls)],
            'update': [obj for obj in session.dirty if isinstance(obj, cls)],
            'delete': [obj for obj in session.deleted if isinstance(obj, cls)]
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            add_to_index(cls.__tablename__, obj)
        for obj in session._changes['update']:
            add_to_index(cls.__tablename__, obj)
        for obj in session._changes['delete']:
            remove_from_index(cls.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id')))
    # Since this is an auxiliary table that has no data other than the
    # foreign keys, it doesn't need to be created as a model class.


class User(UserMixin, db.Model):
    '''Model for the user table'''
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    about_me = db.Column(db.Text(380))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    # one to many relationship:
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    # many to many relationship:
    following = db.relationship('User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return None
        return User.query.get(id)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        # default = 'http%3A%2F%2Fcyan.red%2Fimages%2Fmystery_avatar.png'
        default = 'mm'
        return 'https://www.gravatar.com/avatar/{}?s={}&d={}'.format(digest, size, default)

    def follow(self, user):
        if not self.is_following(user):
            self.following.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        '''This method checks if user to user relationship already exists'''
        return self.following.filter(followers.c.followed_id == user.id).count() > 0
        # looks for items in the association table that have the left side
        # foreign key set to the self user, and the right side set to the user
        # argument. The result of the count() query is going to be 0 or 1, so
        # checking for the count being 1 or greater than 0 is the same.

    def followed_posts(self):
        follow_posts = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own_posts = Post.query.filter_by(user_id=self.id)
        return follow_posts.union(own_posts).order_by(Post.timestamp.desc())


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(SearchableMixin, db.Model):
    '''Model for user posts table'''
    __searchable__ = ['body']
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text(280))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    language = db.Column(db.String(5))
    # one to many relationship:
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)


db.event.listen(db.session, 'before_commit', Post.before_commit)
db.event.listen(db.session, 'after_commit', Post.after_commit)


# db.relationship
# -----------------------------------------------------------------------------
# db.relationship. This is not an actual database field, but a high-level view
# of the relationship between users and posts. For a one-to-many relationship,
# a db.relationship field is normally defined on the "one" side, and is used
# as a convenient way to get access to the "many" (for example, if I have a
# user 'u', the expression u.posts will run a query returning all the posts
# written by that user). The first argument to db.relationship indicates the
# class that represents the "many" side of the relationship. The backref
# argument defines the name of a field that will be added to the objects of
# the "many" class that points back at the "one" object. This will add a
# post.author expression that will return the user given a post.

# The 'following' relationship

'''
followers table:
follower_id  followed_id
u1           u2
u2           u1
u3           u1
u3           u2
u4           u1
'''

# This relationship links User instances to other User instances, so as a
# convention let's say that for a pair of users linked by this relationship,
# the left side user is following the right side user. We're defining the
# relationship as seen from the left side user with the name following.
# When we query this relationship from the left side we'll get the list of
# followed users on the right side.

# 'User' is the right side entity of the relationship (the left side entity is
# the parent class). Since this is a self-referential relationship.

# secondary configures the association table that is used for the relationship.

# primaryjoin indicates the condition that links the left side entity
# (the follower user) with the association table. The join condition for the
# left side of the relationship is the user ID matching the follower_id field
# of the association table. The followers.c.follower_id expression references
# the follower_id column of the association table.

# secondaryjoin indicates the condition that links the right side entity
# (the followed user) with the association table. The only difference is we're
# referencing followed_id, the other foreign key in the association table.

# backref defines how this relationship will be accessed from the right side
# entity. From the left side, the relationship is named following, so from the
# right side I am going to use the name followers to represent all the left
# side users that are linked to the target user in the right side.

# The additional lazy argument indicates the execution mode for this query.
# A mode of dynamic sets up the query to not run until specifically requested,
# which is also how we set up the posts one-to-many relationship. The second
# 'lazy' applies to the left side query instead of the right side.


# Adding & removing follows:
# -----------------------------------------------------------------------------
# Thanks to the SQLAlchemy ORM, a user following another user can be recorded
# in the database working with the followed relationship as if it was a list.
# For example, if we had two users stored in user1 and user2 variables, we can
# make the first follow the second with:

# user1.following.append(user2)

# To stop following the user:

# user1.following.remove(user2)

# Even though we could use these lines anywhere, if we want to promote
# reusability in our code, it might be better to implement the "follow" and
# "unfollow" functionality as methods in the User model. It is always best to
# move the application logic away from view functions and into models or other
# auxiliary classes or modules, it also makes unit testing much easier.


# Post.query.join(...).filter(...).order_by(...)
# -----------------------------------------------------------------------------
# The initial thought to display posts from followed users would be to run a
# query that returns the list of followed users, then for each of these users,
# run a query to get the posts. Once we have all the posts, merge them into a
# single list and sort them by date. This solution is not scalable. If you have
# thousands of users the taxation on memory to store the lists is no good.

# This kind of work is what relational databases excel at. The database has
# indexes that allow it to perform the queries and the sorting in a much more
# efficient. So what we really want is to come up with a single database query
# that defines the information that I want to get, and let the database figure
# out how to extract that information in the most efficient way.

def example_posts(self):
    return Post.query.join(
        followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id).order_by(
                Post.timestamp.desc())

# Post.query.join(followers, (followers.c.followed_id == Post.user_id))

# We're invoking the join operation on the posts table. The first argument is
# the followers association table, and the second argument is the join
# condition. What I'm saying with this call is that I want the database to
# create a temporary table that combines data from posts and followers tables.
# The data is going to be merged according to the condition.

# .filter(followers.c.follower_id == self.id)

# The join operation gives a list of all the posts that are followed by any
# user. We only want a subset of this list, the posts followed by a single
# user, so we trim all the entries we don't need, with a filter() call.

# .order_by(Post.timestamp.desc())

# The final step is to sort by the timestamp field in the Post table.

# The only difference in the code above is that we also want to include our
# own posts along with those we are following. One solution would be to make
# all users follow themselves, but then we would need to remember this and make
# adjustments later on if we were doing things like listing all followers or
# a follower count. Instead we do a query to get all our posts then combine
# them with the followed posts with .union() then do the sorting by timestamp.


# Changing data in the database
# -----------------------------------------------------------------------------
# Changes to a database are done in the context of a session, which can be
# accessed as db.session. Multiple changes can be accumulated in a session and
# once all the changes have been registered you can issue a single
# db.session.commit(), which writes all the changes atomically. If at any time
# while working on a session there is an error, a call to db.session.rollback()
# will abort the session and remove any changes stored in it. The important
# thing to remember is that changes are only written to the database when
# db.session.commit() is called. Sessions guarantee that the database will
# never be left in an inconsistent state. For example:

# >>> u = User(username='rick', email='rick@email.com')
# >>> db.session.add(u)
# >>> db.session.commit()

# All models have a query attribute that is the entry point to run database
# queries. The most basic query is that one that returns all elements of that
# class, which is appropriately named all(). For example:

# >>> users = User.query.all()
# >>> for u in users:
# ...     print(u.id, u.username)

# Another way to query, if you know the id of a user:
# >>> u = User.query.get(2)

# To add a post:
# >>> u = User.query.get(1)
# >>> p = Post(body="I'm pickle rick!", author=u)

# get all posts written by a user (if no posts, returns an empty list):
# >>> u = User.query.get(1)
# >>> posts = u.posts.all()
# >>> posts
# [<Post I'm pickle rick!>, <Post This is another post>]

# print post author and body for all posts:
# >>> posts = Post.query.all()
# >>> for p in posts:
# ...     print(p.id, p.author.username, p.body)

# get all users in reverse alphabetical order:
# >>> User.query.order_by(User.username.desc()).all()

# delete all users and posts:
# >>> users = User.query.all()
# >>> for u in users:
# ...     db.session.delete(u)
#
# >>> posts = Post.query.all()
# >>> for p in posts:
# ...     db.session.delete(p)

# For more see: http://flask-sqlalchemy.pocoo.org/


# Changing the database structure (Flask-Migrate)
# -----------------------------------------------------------------------------
# Remember, anytime you add, remove or modify the columns of a table, you
# need to migrate, then update (see note sin __init__.py):

# (venv) $ flask db migrate -m "Added xyz table"
# (venv) $ flask db upgrade


# password hashes
# -----------------------------------------------------------------------------
# One of the packages that implement password hashing is Werkzeug:

# from werkzeug.security import generate_password_hash, check_password_hash

# hash = generate_password_hash('foobar')
# check_password_hash(hash, 'foobar')     # True
# check_password_hash(hash, 'barfoo')     # False


# Flask-Login
# -----------------------------------------------------------------------------
# The Flask-Login extension works with the application's user model, and
# expects certain properties and methods to be implemented in it. This approach
# is nice, because as long as these required items are added to the model,
# Flask-Login does not have any other requirements. The four requirements:

# - is_authenticated: a property that is True if the user has valid credentials
#   or False otherwise.
# - is_active: a property that is True if the user's account is active or False
#   otherwise.
# - is_anonymous: a property that is False for regular users, and True for a
#   special, anonymous user.
# - get_id(): a method that returns a unique identifier for the user as a
#   string (unicode, if using Python 2).

# We can implement these four properties ourselves or just include a 'mixin'
# class called UserMixin that includes generic implementations that are
# appropriate for most user model classes.

# Oh, but wait, there's more:

# Flask-Login keeps track of the logged in user by storing its unique
# identifier in Flask's user session, a storage space assigned to each user who
# connects to the application. Each time the logged-in user navigates to a
# new page, Flask-Login retrieves the ID of the user from the session, and then
# loads that user into memory. Because Flask-Login knows nothing about
# databases, it needs the application's help in loading a user. For that reason,
# the extension expects that the application will configure a user loader
# function, that can be called to load a user given the ID.


# Password reset tokens:
# -----------------------------------------------------------------------------
# How do JWTs work? Here's a quick Python shell example:

# >>> import jwt
# >>> token = jwt.encode({'a': 'b'}, 'my-secret', algorithm='HS256')
# >>> token
# b'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhIjoiYiJ9.dvOo58OBDHiuSHD4uW...'
# >>> jwt.decode(token, 'my-secret', algorithms=['HS256'])
# {'a': 'b'}

# The {'a': 'b'} dictionary is an example payload that is going to be written
# into the token. To make the token secure, a secret key needs to be provided
# to be used in creating a cryptographic signature. This example uses a string,
# but with the application we use the SECRET_KEY from the config. The algorithm
# argument specifies how the token is to be generated. HS256 is the most
# widely used.

# The resulting token is a long sequence of characters. But this is NOT an
# encrypted token. The contents, including the payload, can be decoded easily
# by anyone. What makes the token secure is that the payload is signed. If
# somebody tried to forge or tamper with the payload in a token, then the
# signature would be invalidated, and to generate a new signature the secret
# key is needed. When a token is verified, the contents of the payload are
# decoded and returned back to the caller.

# The payload we're using for the password reset tokens has the format
# {'reset_password': user_id, 'exp': token_expiration}. The exp field is
# standard for JWTs - it indicates an expiration time for the token.

# When the user clicks on the emailed link, the token is going to be sent back
# to the application as part of the URL, and the first thing the view function
# that handles this URL will do is to verify it. If the signature is valid,
# then the user can be identified by the ID stored in the payload.

# The get_reset_password_token() function generates a JWT token as a string.
# The decode('utf-8') is necessary because the jwt.encode() function returns
# the token as a byte sequence, but in the application it is more convenient
# to have the token as a string.

# The verify_reset_password_token()
# This method takes a token and attempts to decode it by invoking PyJWT's
# jwt.decode() function. If the token cannot be validated or is expired, an
# exception will be raised, and in that case we catch it to prevent the error,
# and return None to the caller. If the token is valid, then the value of the
# reset_password key from the token's payload is the ID of the user, so we can
# load the user and return it.


# SearchableMixin()
# -----------------------------------------------------------------------------
# Just as a reminder, a class method is associated with the class and not a
# particular instance. The use of cls instaed of self, makes it clear that
# this method receives a class and not an instance as its first argument. Once
# attached to the Post model for example, the search() method above would be
# invoked as Post.search(), without having to have an actual instance of class.

# The search() class method wraps the query_index() function from app/search.py
# to replace the list of object IDs with actual objects. You can see that the
# first thing this function does is call query_index(), passing
# cls.__tablename__ as the index name. This is going to be a convention, all
# indexes will be named with the name Flask-SQLAlchemy assigned to the
# relational table.

# The SQLAlchemy query that retrieves the list of objects by their IDs is based
# on a CASE statement from the SQL language, which needs to be used to ensure
# that the results from the database come in the same order as the IDs are
# given. This is important because the Elasticsearch query returns results
# sorted from more to less relevant.

# The before_commit() and after_commit() methods are going to respond to two
# events from SQLAlchemy, which are triggered before and after a commit takes
# place. The before handler is useful because the session hasn't been committed
# yet, so we can look at it and figure out what objects are going to be added,
# modified and deleted: available as session.new, session.dirty and
# session.deleted respectively. These objects are not going to be available
# after the session is committed, so we need to save them before the commit
# takes place. We use a session._changes dictionary to write these objects
# and as soon as the session is committed we'll be using them to update the
# Elasticsearch index.

# When the after_commit() handler is invoked, we can now make changes on the
# Elasticsearch side. The session object has the _changes variable that we
# added in before_commit(), so now we can iterate over the added, modified and
# deleted objects and make the corresponding calls to the indexing functions
# in app/search.py.

# The reindex() class method is a simple helper method that you can use to
# refresh an index with all the data from the relational side. With this method
# we can issue Post.reindex() to add all the posts in the database to the
# search index.

# To incorporate the SearchableMixin class into the Post model we add it as a
# subclass, and also "hook up" the before and after commit events:

# db.event.listen(db.session, 'before_commit', Post.before_commit)
# db.event.listen(db.session, 'after_commit', Post.after_commit)

# Note that the db.event.listen() calls are not inside the class, but after it.
# Now the Post model is automatically maintaining a full-text search index for
# posts. We can use the reindex() method to initialize the index from all the
# posts currently in the database. In the flask shell run:

# >>> Post.reindex()

# Then try a search:
# >>> query, total = Post.search('flask', 1, 10)
# >>> total
# 3

# Remember, if we need to add search support for a different database model,
# we can simply do so by adding the SearchableMixin class to it,
# the __searchable__ attribute with the list of fields to index and the
# SQLAlchemy event handler connections.


# misc notes:
# -----------------------------------------------------------------------------
# Note that setting a VARCHAR (maximum string length) helps a database optimize
# its space usage.

# Note that we don't include the () after datetime.utcnow, because we want to
# pass the function itself, and not the result of calling it.
