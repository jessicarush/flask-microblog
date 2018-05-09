from datetime import datetime
from flask import g, flash, jsonify, render_template, redirect, request, \
    url_for, current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from guess_language import guess_language
from app import db
from app.main.forms import EditProfileForm, PostForm, SearchForm, MessageForm
from app.models import User, Post, Message, Notification
from app.translate import translate
from app.main import bp


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        # there is no db.session.add() before the commit, because when you
        # reference current_user, Flask-Login will invoke the user loader
        # callback function, which will run a database query that will put the
        # target user in the database session. So you can add the user again
        # in this function, but it's not necessary because it's already there.
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})
    # Invoke the translate() function and pass the three arguments directly
    # from the data that was submitted with the request. The result is
    # incorporated into a single-key dictionary which is passed as an argument
    # to Flask's jsonify() function, which converts the dictionary to a JSON
    # formatted payload. The return value from jsonify() is the HTTP response
    # that is going to be sent back to the client.


@bp.route('/home', methods=['GET', 'POST'])
@login_required
def index():
    '''View function for the main index page.'''
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        # Each time a post is submitted, we run the text through the
        # guess_language function to try to determine the language. If it
        # comes back as unknown or an unexpectedly long result, we play it
        # safe and save an empty string to the database.
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Posted!'))
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) if posts.has_prev else None
    return render_template('index.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url, prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) if posts.has_prev else None
    return render_template('index.html', title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/about')
@login_required
def about():
    return render_template('about.html', title='About')


@bp.route('/user/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        # Each time a post is submitted, we run the text through the
        # guess_language function to try to determine the language. If it
        # comes back as unknown or an unexpectedly long result, we play it
        # safe and save an empty string to the database.
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Posted!'))
        return redirect(url_for('main.user', username=username))
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('user.html', user=user, form=form, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username, current_user.email)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_("You can't follow yourself."))
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(_('You are following %(username)s.', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_("You can't unfollow yourself."))
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You are not following %(username)s.', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])


@bp.route('/export_posts')
@login_required
def export_posts():
    if current_user.get_task_in_progress('export_posts'):
        flash(_('An export is currently in progress'))
    else:
        current_user.launch_task('export_posts', _('Exporting posts...'))
        db.session.commit()
    return redirect(url_for('main.user', username=current_user.username))


# render_template()
# -----------------------------------------------------------------------------
# The render_template() function invokes the Jinja2 template engine that
# comes with the Flask framework. Jinja2 substitutes {{ ... }} blocks with
# the corresponding values, given by the arguments provided in the
# render_template() call. Templates also support control statements, given
# inside {% ... %} blocks.


# redirect() and the Post/Redirect/Get pattern
# -----------------------------------------------------------------------------
# This function instructs the client web browser to automatically
# navigate to a different page, given as an argument. Notice in the index
# view how there is a redirect after the user submits the post form. Why the
# redirect? It is a standard practice to respond to a POST request generated by
# a web form submission with a redirect. This helps mitigate an annoyance with
# how the refresh command is implemented in web browsers. All the web browser
# does when you hit the refresh key is to re-issue the last request. If a POST
# request with a form submission returns a regular response, then a refresh
# will re-submit the form. Because this is unexpected, the browser is going to
# ask the user to confirm the duplicate submission, but most users will not
# understand what the browser is asking them. But if a POST request is answered
# with a redirect, the browser is now instructed to send a GET request to grab
# the page indicated in the redirect, so now the last request is not a POST
# request anymore, and the refresh command works in a more predictable way.

# This simple trick is called the Post/Redirect/Get pattern. It avoids
# inserting duplicate posts when a user inadvertently refreshes the page
# after submitting a web form. https://en.wikipedia.org/wiki/Post/Redirect/Get


# Flask-WTF
# -----------------------------------------------------------------------------
# Flask-WTF makes the job of processing the data submitted by the user really
# easy. Note the methods argument in the route decorator. This tells Flask that
# this view function accepts GET and POST requests, overriding the default,
# which is to accept only GET requests. The HTTP protocol states that GET
# requests are those that return information to the client. POST requests are
# typically used when the browser submits form data to the server (in reality
# GET requests can also be used for this purpose, but it's not a recommended
# as it adds the form fields to the URL, cluttering the browser address bar.)

# The form.validate_on_submit() method does all the form processing work. When
# the browser sends the GET request to receive the web page with the form,
# this method is going to return False, so in that case the function skips the
# if statement and goes directly to render the template in the last line.
# When the browser sends the POST request as a result of the user pressing the
# submit button, form.validate_on_submit() is going to gather all the data,
# run all the validators attached to fields, and if everything is all right it
# will return True.


# flash()
# -----------------------------------------------------------------------------
# The flash() function is a useful way to show a message to the user. A lot of
# applications use this technique to let the user know if some action has been
# successful. This flash message needs to also be added to the jinja template
# for it to be seen.


# login(), @login_required
# -----------------------------------------------------------------------------
# The top two lines in the login() function deal with a situation where a user
# that is already logged in, accidentally navigates to the /login URL. We'll
# assume thats a mistake and redirect them to the index page. The current_user
# variable comes from Flask-Login and can be used at any time during the
# handling to obtain the user object that represents the client of the request.
# The value of this variable can be a user object from the database (which
# Flask-Login reads through the @login.user_loader callback in models.py),
# or a special anonymous user object if the user did not log in yet.
# is_authenticated (one of the one of the Flask-Login required properties
# that's made for us in the UserMixin) checks if the user is logged in or not.

# When a user that is not logged in accesses a view function protected with the
# @login_required decorator, the decorator is going to redirect to the
# login page, but it is going to include some extra information in this
# redirect so that the application can then return to the page the user was
# trying to access once they're logged in. It does this by adding a query
# string argument to the URL: /login?next=/index. The next query string
# argument is set to the original URL, so the app can use that to redirect back
# after login. Here's the related code:

# next_page = request.args.get('next')
# if not next_page or url_parse(next_page).netloc != '':
#     next_page = url_for('main.index')
# return redirect(next_page)

# There are actually three possible cases that need to be considered to
# determine where to redirect after a successful login:
    # - the URL does not have a next argument, then the user is redirected to
    #   the index page.
    # - the URL includes a next argument that is set to a relative path, then
    #   the user is redirected to that URL.
    # - the URL includes a next argument that is set to a full URL that
    #   includes a domain name, then the user is redirected to the index page.

# The first and second cases are self-explanatory. The third case is to make
# the application more secure. An attacker could insert a malicious URL into
# the next argument, so the application only redirects when the URL is relative,
# which ensures that the redirect stays within the same site as the application.
# To determine if the URL is relative or absolute, we parse it with Werkzeug's
# url_parse() function and then check if the netloc component is set or not.

# Note: Until there's a registration, create a user in the database this way:

# $ flask shell
# >>> u = User(username='rick', email='rick@example.com')
# >>> u.set_password('pickle')
# >>> db.session.add(u)
# >>> db.session.commit()


# first_or_404()
# -----------------------------------------------------------------------------
# A database query can be executed by calling all() if you want to get all
# results, or first() if you want to get just the first result or None if there
# are zero results. A variant of first() is first_or_404(), which works exactly
# like first() when there are results, but in the case that there are no
# results, it automatically sends a 404 error back to the client. Executing the
# query in this way I save myself from checking if the query returned a user,
# because when the username does not exist in the database the function will
# not return and instead a 404 exception will be raised.


# @app.before_request (@bp.before_app_request)
# -----------------------------------------------------------------------------
# The @app.before_request decorator allows us to execute something before any
# other view function in the application.


# g.search_form = SearchForm()
# -----------------------------------------------------------------------------
# Here we create an instance of the search form class when we have an
# authenticated user. But of course, we need this form object to persist until
# it can be rendered at the end of the request, so we need to store it
# somewhere. That somewhere is going to be the g container, provided by Flask.
# This g variable provided by Flask is a place where the application can store
# data that needs to persist through the life of a request. Here we're storing
# the form in g.search_form, so when the before request handler ends and Flask
# invokes the view function that handles the requested URL, the g object is
# going to be the same, and will still have the form attached to it. It's
# important to note that this g variable is specific to each request and each
# client, so even if your web server is handling multiple requests at a time
# for different clients, you can still rely on g to work as private storage
# for each request, independently of what goes on in other requests that are
# handled concurrently.

# The next step is to render the form to the page. Since we want this form in
# all pages, it makes sense to add it to base.html. This turns out to be simple,
# because templates can also see the data stored in the g variable, so we don't
# need to worry about adding the form as an explicit template argument in all
# the render_template() calls in the application!


# pagination()
# -----------------------------------------------------------------------------
# Flask-SQLAlchemy supports pagination natively with the paginate() query
# method. If for example, I want to get the first twenty followed posts of the
# user, I can replace the all() call that terminates the query with:

# user.followed_posts().paginate(1, 20, False).items

# The paginate method can be called on any query object from Flask-SQLAlchemy.
# It takes three arguments:

    # - the page number, starting from 1
    # - the number of items per page
    # - an error flag. If True, when an out of range page is requested a 404
    #   error will be automatically returned to the client. If False, an empty
    #   list will be returned for out of range pages.

# The return value from paginate is a Pagination object. The items attribute of
# this object contains the list of items in the requested page.

# Consider how the page number is going to be incorporated into application
# URLs. A fairly common way is to use a query string argument to specify an
# optional page number, defaulting to page 1 if it is not given.
# Here are some example URLs:

    # - Page 1, implicit: http://localhost:5000/index
    # - Page 1, explicit: http://localhost:5000/index?page=1
    # - Page 3: http://localhost:5000/index?page=3

# To access arguments given in the query string, we can use Flask's
# request.args object.

# page = request.args.get('page', 1, type=int)

# the routes determine the page number to display, either from the page query
# string argument or a default of 1. Then we replace the .all() on the posts
# query object with:

# ....paginate(page, app.config['POSTS_PER_PAGE'], False)

# Lastly, when we render the template we have to say posts=posts.items instead
# of posts=posts. That's it. You can now access the other pages by adding
# ?page=2 to the url. As mentioned, paginate returns a Pagination object. This
# object has a few other attributes that are useful when building page links:

    # has_next: True if there is at least one more page after the current one
    # has_prev: True if there is at least one more page before the current one
    # next_num: page number for the next page
    # prev_num: page number for the previous page

# next_url = url_for('main.index', page=posts.next_num) if posts.has_next else None
# prev_url = url_for('main.index', page=posts.prev_num) if posts.has_prev else None

# One interesting aspect of the url_for() function is that you can add any
# keyword arguments to it, and if the names of those arguments are not
# referenced in the URL directly, then Flask will include them in the URL
# as query arguments.
