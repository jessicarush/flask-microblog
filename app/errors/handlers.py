from flask import render_template
from app import db
from app.errors import bp


@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# @bp.app_errorhandler
# -----------------------------------------------------------------------------
# Instead of attaching the error handlers to the application with the
# @app.errorhandler decorator, I use the blueprint's @bp.app_errorhandler
# decorator. While both decorators achieve the same result, the idea is to try
# to make the blueprint independent of the app so that it's more portable.
