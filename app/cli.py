import os
import click


def register(app):
    @app.cli.group()
    def translate():
        '''Translation and localization commands'''
        pass

    @translate.command()
    def update():
        '''Update all languages.'''
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d app/translations'):
            raise RuntimeError('update command failed')
        os.remove('messages.pot')

    @translate.command()
    def compile():
        '''Compile all languages.'''
        if os.system('pybabel compile -d app/translations'):
            raise RuntimeError('compile command failed')

    @translate.command()
    @click.argument('lang')
    def init(lang):
        '''Initialize a new language.'''
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system(
                'pybabel init -i messages.pot -d app/translations -l ' + lang):
            raise RuntimeError('init command failed')
        os.remove('messages.pot')


# register(app)
# -----------------------------------------------------------------------------
# Following the implemenation of the factory function in app/__init__.py:
# the current_app variable does not work in this case because these commands
# are registered at start up, not during the handling of a request, which is
# the only time when current_app can be used. To remove the reference to app
# in this module, we resorted to another trick, which is to move these custom
# commands inside a register() function that takes the app instance as an arg.


# @translate.command()
# -----------------------------------------------------------------------------
# Note how the decorator from these functions is derived from the translate
# parent function. This may seem confusing, since translate() is a function,
# but it is the standard way in which Click builds groups of commands.

# For all commands, we run them and make sure that the return value is zero,
# which implies that the command did not return any error.

# The init command uses the @click.argument decorator to define the language
# code. Click passes the value provided in the command to the handler function
# as an argument, and then I incorporate the argument into the init command.

# The final step to enable these commands to work is to import them
# (from app import cli). This can be done in the top-level directory in
# microblog.py.

# Run microblog.py at least once to register the commands. Note it doesn't
# need to be currently running after that to run the translate commands.

# At this point, running flask --help will list the translate command as an
# option. And flask translate --help will show the three sub-commands defined.

# To add a new language, you use:

# (venv) $ flask translate init <language-code>

# To update all the languages after making changes to the _() and _l()
# language markers:

# (venv) $ flask translate update

# To compile all languages after updating the translation files:

# (venv) $ flask translate compile
