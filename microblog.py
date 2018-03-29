from app import create_app, db, cli
from app.models import User, Post

app = create_app()
cli.register(app)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}

# Instead of running a python interpreter session, you can run a flask shell
# session. This is basically the same thing but it pre-imports 'app' and you
# can configure a "shell context" – a list of other symbols to pre-import.

# The app.shell_context_processor decorator registers the function as a shell
# context function. When the flask shell command runs, it will invoke this
# function and register the items returned by it in the shell session. After
# you add the shell context processor function you can work with database
# entities without having to import them:

# (venv) $ flask shell

# To run flask, you can set the FLASK_APP environment variable:
# (venv) $ export FLASK_APP=microblog.py
# (venv) $ flask run
# To activate debug mode:
# (venv) $ export FLASK_DEBUG=1

# or...

if __name__ == '__main__':
    app.run(debug=False)
