import json
import requests
from flask import current_app
from flask_babel import _


# def translate(text, source_language, dest_language):
#     if 'MS_TRANSLATOR_KEY' not in current_app.config or not current_app.config['MS_TRANSLATOR_KEY']:
#         return _('Error: translation service is not configured.')
#
#     auth = {'Ocp-Apim-Subscription-Key': current_app.config['MS_TRANSLATOR_KEY']}
#     url = ('https://api.microsofttranslator.com/v2/Ajax.svc/Translate?'
#            'text={}&from={}&to={}'.format(text, source_language, dest_language))
#     r = requests.get(url, headers=auth)
#
#     if r.status_code != 200:
#         return _('Error: translation service failed.')
#     return json.loads(r.content.decode('utf-8-sig'))


# NOTE: MS Translator changed from V2 to V3
# https://docs.microsoft.com/en-us/azure/cognitive-services/translator/quickstart-python-translate
# https://docs.microsoft.com/en-us/azure/cognitive-services/translator/reference/v3-0-translate?tabs=curl
# https://github.com/MicrosoftTranslator/Text-Translation-API-V3-Python/blob/master/Translate.py



def translate(text, source_language, dest_language):
    if 'MS_TRANSLATOR_KEY' not in current_app.config or not current_app.config['MS_TRANSLATOR_KEY']:
        return _('Error: translation service is not configured.')

    base_url = 'https://api.cognitive.microsofttranslator.com'
    path = '/translate?api-version=3.0'
    params = '&from={}&to={}'.format(source_language, dest_language)
    url = base_url + path + params
    auth = {'Ocp-Apim-Subscription-Key': current_app.config['MS_TRANSLATOR_KEY']}
    body = [{'text': text}]

    r = requests.post(url, headers=auth, json=body)

    # You can get the response like this:
    # response = r.json()
    # It looks like this:
    # print(response)
    # [{'translations': [{'text': "Bonjour", 'to': 'fr'}]}]
    # To get just the translated text:
    # print(response[0]['translations'][0]['text'])

    if r.status_code != 200:
        return _('Error: translation service failed.')

    return r.json()[0]['translations'][0]['text']


# Note this code is for the Ajax translation of the user posts only
# (using Microsofts Azure Translator Text API).

# The get() method from the requests package sends an HTTP request with a
# GET method to the URL given as the first argument. We're using the
# /v2/Ajax.svc/Translate URL, which is an endpoint from the translation
# service that returns translations as a JSON payload. The text, source and
# destination languages need to be given as query string arguments in the URL,
# named text, from and to respectively. To authenticate with the service, we
# need to pass the key that we added to the config. This key needs to be given
# in a custom HTTP header with the name Ocp-Apim-Subscription-Key. We do this
# by creating the auth dictionary with this header as they key and then pass
# it to requests in the headers argument.

# The requests.get() method returns a response object. If the status code is
# 200, then the body of the response has a JSON encoded string with the
# translation, so all we need to do is use the json.loads() function (from the
# standard library) to decode the JSON into a Python string. The content
# attribute of the response object contains the raw body of the response as a
# bytes object, which is converted to a UTF-8 string and sent to json.loads().
