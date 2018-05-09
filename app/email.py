from threading import Thread
from flask import current_app
from flask_mail import Message
from app import mail


def send_asynchronous(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body,
               attachments=None, sync=False):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    else:
        Thread(target=send_asynchronous,
            args=(current_app._get_current_object(), msg)).start()


# Asynchronous emails
# -----------------------------------------------------------------------------
# Sending an email can slow down the application down considerably. It usually
# takes a few seconds to get an email out, and maybe more if the email server of
# the addressee is slow, or if there are multiple addressees.

# What we really want is for the send_email() function to be asynchronous. This
# can be done through the threading and multiprocessing modules. Starting a
# background thread for email is much less resource intensive than starting a
# brand new process, so we'll go with that approach.

# Note in the send_asynchronous function we're passing not only the message,
# but the flask app as well**. When working with threads there is an important
# design aspect of Flask that needs to be kept in mind. Flask uses contexts to
# avoid having to pass arguments across functions. Know that there are two
# types of contexts, the application context and the request context. In most
# cases, these contexts are automatically managed by the framework, but when
# the application starts custom threads, contexts for those threads may need to
# be manually created.

# There are many extensions that require an application context to be in place
# to work, because that allows them to find the Flask application instance
# without it being passed as an argument. The reason many extensions need to
# know the application instance is because they have their configuration stored
# in the app.config object. This is exactly the situation with Flask-Mail.
# The mail.send() method needs to access the configuration values for the email
# server, and that can only be done by knowing what the application is. The
# application context that is created with the with app.app_context() call
# makes the app instance accessible via the current_app variable from Flask.

# In the send_email function, here's where we're actually calling the
# send_asynchronous() function... as the target of a new Thread. Before we
# created a "factory function" in app/__init__.py the args here would have
# been 'args=(app, msg)' but now we're using current_app. Unfortunately, we
# can't just replace app with current_app. Remember, this function runs in a
# separate background thread. current_app is a context-aware variable that is
# tied to the thread that is handling the client request. In a different thread,
# current_app would not have a value assigned. current_app is really a
# 'proxy object' that is dynamically mapped to the application instance. What
# we need to do is access the real application instance that is stored inside
# this proxy object, and pass that as the app argument.
# The current_app._get_current_object() expression does exactly that.
