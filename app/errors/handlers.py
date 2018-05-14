from flask import render_template, request
from app import db
from app.errors import bp
from app.api.errors import error_response as api_error_response


def wants_json_response():
    return request.accept_mimetypes['application/json'] >= \
        request.accept_mimetypes['text/html']


@bp.app_errorhandler(404)
def not_found_error(error):
    if wants_json_response():
        return api_error_response(404)
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if wants_json_response():
        return api_error_response(500)
    return render_template('errors/500.html'), 500


# @bp.app_errorhandler
# -----------------------------------------------------------------------------
# Instead of attaching the error handlers to the application with the
# @app.errorhandler decorator, I use the blueprint's @bp.app_errorhandler
# decorator. While both decorators achieve the same result, the idea is to try
# to make the blueprint independent of the app so that it's more portable.


# wants_json_response()
# -----------------------------------------------------------------------------
# The HTTP protocol supports a mechanism by which the client and the server can
# agree on the best format for a response, called content negotiation. The
# client needs to send an Accept header with the request, indicating the format
# preferences. The server then looks at the list and responds using the best
# format it supports from the list offered by the client.

# What I want to do is modify the global application error handlers so that
# they use content negotiation to reply in HTML or JSON according to the client
# preferences. This can be done using Flask's request.accept_mimetypes object.
