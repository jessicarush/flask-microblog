import json
import sys
import time
from flask import render_template
from rq import get_current_job
from app import create_app, db
from app.email import send_email
from app.models import Task, User, Post


app = create_app()
app.app_context().push()


def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        task.user.add_notification(
            'task_progress', {'task_id': job.get_id(), 'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()


def export_posts(user_id):
    try:
        # read user posts from database:
        user = User.query.get(user_id)
        _set_task_progress(0)
        data = []
        i = 0
        total_posts = user.posts.count()
        for post in user.posts.order_by(Post.timestamp.asc()):
            data.append({'body': post.body,
                         'timestamp': post.timestamp.isoformat() + 'Z'})
            time.sleep(0.1) # NOTE: this is only here so we can see the progress
            i += 1
            _set_task_progress(100 * i // total_posts)

        # send email with data to user:
        send_email('Microblog: Your blog posts',
                sender=app.config['ADMINS'][0], recipients=[user.email],
                text_body=render_template('email/export_posts.txt', user=user),
                html_body=render_template('email/export_posts.html', user=user),
                attachments=[('posts.json', 'application/json',
                              json.dumps({'posts': data}, indent=4))], sync=True)
    except:
        # handle unexpected errors:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())

    # Why wrap the whole task in a try/except block? The application code
    # that exists in request handlers is protected against unexpected errors
    # because Flask itself catches exceptions and then handles them observing
    # any error handlers and logging configuration I have set up for the
    # application. This function, however, is going to run in a separate
    # process that is controlled by RQ, not Flask, so if any unexpected errors
    # occur the task will abort, RQ will display the error to the console and
    # then will go back to wait for new jobs. So basically, unless you are
    # watching the output of the RQ worker or logging it to a file, you will
    # never find out there was an error.
