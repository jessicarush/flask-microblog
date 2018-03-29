from flask import current_app


def add_to_index(index, model):
    if not current_app.elasticsearch:
        return
    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model, field)
    current_app.elasticsearch.index(index=index, doc_type=index, id=model.id,
                                    body=payload)

def remove_from_index(index, model):
    # (assuming one day we'll support deleting blog posts)
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, doc_type=index, id=model.id)


def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return [], 0
    search = current_app.elasticsearch.search(
        index=index, doc_type=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*']}},
              'from': (page - 1) * per_page, 'size': per_page})
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']


# All the code that interacts with the Elasticsearch index is in this module.
# The rest of the application will use the functions in this module to access
# the index but will not have direct access to Elasticsearch. This is
# important, because if one day you decided you want to switch to a different
# engine, all you need to do is rewrite the functions in this module, and the
# application will continue to work as before.

# These functions all start by checking if app.elasticsearch is None, and in
# that case return without doing anything. This is so that when the
# Elasticsearch server isn't configured, the application continues to run
# without the search capability and without giving any errors. This is just
# as a matter of convenience during development or when running unit tests.

# The functions accept the index name as an argument. In all the calls we're
# passing down to Elasticsearch, we're using this name as the index name and
# also as the document type.

# The functions that add and remove entries from the index take the SQLAlchemy
# model as a second argument. Elasticsearch documents also needed a unique
# identifier. For that we're using the id field of the SQLAlchemy model, which
# is also unique.

# The query_index() function takes the index name and a text to search for,
# along with pagination controls, so that search results can be paginated like
# Flask-SQLAlchemy results are. 'multi_match' is the query type which can
# search across multiple fields. Other query types include: match,
# match_phrase, common_terms, and more:
# https://www.elastic.co/guide/en/elasticsearch/reference/current/full-text-queries.html

# By passing a field name of *, we're telling Elasticsearch to look in all the
# fields, so basically we're searching the entire index. This is useful in
# terms of making this function generic, since different models can have d
# ifferent field names in the index.

# The body argument to elasticsearch.search() includes pagination arguments in
# addition to the query itself. The from and size arguments control what subset
# of the entire result set needs to be returned. Elasticsearch does not provide
# a nice Pagination object like the one from Flask-SQLAlchemy, so we have to do
# the pagination math to calculate the from value.

# The query_index() function returns two values: the first is a list of id
# elements for the search results, and the second is the total number of
# results. Both are obtained from the Python dictionary returned by the
# elasticsearch.search() function. In this case we're using list comprehensions
# to extract the id values from the much larger list of results provided by
# Elasticsearch.

# One problem is that this solution requires the application to explicitly
# issue indexing calls as posts are added or removed, which is not terrible,
# but less than ideal, since a bug that causes a missed indexing call when
# making a change on the SQLAlchemy side is not going to be easily detected.
# The two databases will get out of sync more and more each time the bug
# occurs. A better solution would be for these indexing calls to be triggered
# automatically as changes are made on the SQLAlchemy database. We'll do this
# using SQLAlchemy 'events'.

# http://docs.sqlalchemy.org/en/latest/core/event.html

# SQLAlchemy provides a large list of events that applications can be notified
# about. For example, each time a session is committed, we can have a function
# in the application invoked by SQLAlchemy, and in that function we can apply
# the same updates that were made on the SQLAlchemy session to the
# Elasticsearch index. We'll do all this using a 'mixin' class (see models.py).
# This class will act as a "glue" layer between the SQLAlchemy and
# Elasticsearch worlds.
