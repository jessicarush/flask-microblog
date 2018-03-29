from datetime import datetime, timedelta
import unittest
from app import create_app, db
from app.models import User, Post
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='susan')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_avatar(self):
        u = User(username='john', email='john@example.com')
        url = ('https://www.gravatar.com/avatar/d4c74594d841139328695756648b6bd6'
               '?s=100&d=http%3A%2F%2Fcyan.red%2Fimages%2Fmystery_avatar.png')
        self.assertEqual(u.avatar(100), url)

    def test_follow(self):
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        self.assertEqual(u1.following.all(), [])
        self.assertEqual(u1.followers.all(), [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.following.count(), 1)
        self.assertEqual(u1.following.first().username, 'susan')
        self.assertEqual(u2.followers.count(), 1)
        self.assertEqual(u2.followers.first().username, 'john')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.following.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

    def test_follow_posts(self):
        # create four users
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        u3 = User(username='mary', email='mary@example.com')
        u4 = User(username='david', email='david@example.com')
        db.session.add_all([u1, u2, u3, u4])

        # create four posts
        now = datetime.utcnow()
        p1 = Post(body="john's post", author=u1, timestamp=now + timedelta(seconds=1))
        p2 = Post(body="susan's post", author=u2, timestamp=now + timedelta(seconds=4))
        p3 = Post(body="mary's post", author=u3, timestamp=now + timedelta(seconds=3))
        p4 = Post(body="david's post", author=u4, timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # setup the followers
        u1.follow(u2)  # john follows susan
        u1.follow(u4)  # john follows david
        u2.follow(u3)  # susan follows mary
        u3.follow(u4)  # mary follows david
        db.session.commit()

        # check the followed posts of each user
        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])

if __name__ == '__main__':
    unittest.main(verbosity=2)


# Much of the work we related to creating the 'factory function' in
# app/__init__.py had the goal of improving the unit testing workflow. When
# you're running unit tests you want to make sure the application is configured
# in a way that it does not interfere with your development resources, such as
# your database! The previous version of tests.py resorted to a trick of
# modifying the configuration after it was applied to the application instance,
# which is a dangerous practice as not all types of changes will work when done
# that late. What we want instead is to specify a testing configuration before
# it gets added to the application. The create_app() function now accepts a
# config class as an argument. By default, the Config class defined in
# config.py is used, but we can now create an application instance that uses
# a different config simply by passing a new class to the factory function.

# The new application will be stored in self.app, but creating an application
# isn't enough to make everything work. Consider the db.create_all() statement
# that creates the database tables. The db instance needs to know what the
# application instance is, because it needs to get the database URI from
# app.config, but when you are working with an application factory you are
# not really limited to a single application, there could be more than one.
# So how does db know to use the self.app instance that I just created?

# The answer is in the application context. Remember the current_app variable,
# which somehow acts as a proxy for the application when there is no global
# application to import? This variable looks for an active application context
# in the current thread, and if it finds one, it gets the application from it.
# If there is no context, then there is no way to know what application is
# active, so current_app raises an exception.

# Before invoking your view functions, Flask pushes an application context,
# which brings current_app, and g to life. When the request is complete, the
# context is removed, along with these variables. For the db.create_all()
# call to work in the unit testing setUp() method, I pushed an application
# context for the application instance I just created, and in that way,
# db.create_all() can use current_app.config to know where is the database.
# Then in the tearDown() method I pop the context to reset everything to a
# clean state.

# You should also know that the application context is one of two contexts
# that Flask uses. There is also a request context, which is more specific,
# as it applies to a request. When a request context is activated right before
# a request is handled, Flask's request and session variables become available,
# as well as Flask-Login's current_user.
