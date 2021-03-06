# @name: wikidata.py
# @version: 0.1
# @creation_date: 2021-10-21
# @license: The MIT License <https://opensource.org/licenses/MIT>
# @author: Simon Bowie <ad7588@coventry.ac.uk>
# @purpose: Performs functions against the Wikidata API
# @acknowledgements:
# Wikidata API Sandbox: https://www.wikidata.org/wiki/Special:ApiSandbox
# Wikibase authentication code: https://github.com/HeardLibrary/digital-scholarship/blob/master/code/wikibase/api/write-statements.py

import requests
import json
import os
import urllib

# Global variables
resource_url = '/w/api.php'
# Instantiate session outside of any function so that it's globally accessible.
session = requests.Session()

def get_url():
    endpoint_url = os.environ.get('wikidata_url')
    api_url = endpoint_url + resource_url
    return api_url

def get_property_values():
    # get Wikidata property variables from OS environment variables: set in env file passed through Docker Compose
    property_values = dict(
        instance_of=os.environ.get('instance_of'),
        edition_of=os.environ.get('edition_of'),
        has_edition=os.environ.get('has_edition'),
        title=os.environ.get('title'),
        subtitle=os.environ.get('subtitle'),
        author=os.environ.get('author'),
        editor=os.environ.get('editor'),
        translator=os.environ.get('translator'),
        contributor=os.environ.get('contributor'),
        main_subject=os.environ.get('main_subject'),
        publication_date=os.environ.get('publication_date'),
        publisher=os.environ.get('publisher'),
        publication_place=os.environ.get('publication_place'),
        page_count=os.environ.get('page_count'),
        copyright_license=os.environ.get('copyright_license'),
        copyright_status=os.environ.get('copyright_status'),
        doi=os.environ.get('doi'),
        isbn_13=os.environ.get('isbn_13'),
        lccn=os.environ.get('lccn'),
        url=os.environ.get('url')
    )
    return property_values

# get Wikidata entities such as 'written work' or CC licenses
def get_constant_entities():
    wikidata_constants = dict(
        written_work=os.environ.get('written_work'),
        version=os.environ.get('version')
    )
    return wikidata_constants

def authenticate():
    endpoint_url = os.environ.get('wikidata_url')
    username = os.environ.get('username')
    password = os.environ.get('password')
    api_url = endpoint_url + resource_url

    # Request for token for data-modifying actions
    # https://www.wikidata.org/w/api.php?action=help&modules=query%2Btokens
    parameters = dict(
        format='json',
        action='query',
        meta='tokens',
        type='login'
    )
    r = session.get(url=api_url, params=parameters)
    json = r.json()
    login_token = json['query']['tokens']['logintoken']

    # The result of this part is a successful session login.
    # See example at https://www.mediawiki.org/wiki/API:Login
    parameters = dict(
        format='json',
        action='login',
        lgname=username,
        lgpassword=password,
        lgtoken=login_token
    )
    r = session.post(api_url, data=parameters)

    # The CSRF (edit) token is an edit token that is actually used to authorize particular write actions
    # It is used to prevent cross-site request forgery (csrf) attacks. I think it's primarily relevant when web forms are used
    # Here's the page that shows how to get an edit token
    # https://www.mediawiki.org/wiki/API:Edit
    parameters = dict(
        action='query',
        meta='tokens',
        format='json'
    )
    r = session.get(url=api_url, params=parameters)
    data = r.json()
    # The response looks like this:
    # {'batchcomplete': '', 'query': {'tokens': {'csrftoken': '6bc490bb0d2e78cb3f8a2b94e8159da85cdc2484+\\'}}}
    CSRF_token = data['query']['tokens']['csrftoken']
    return [api_url, CSRF_token]

# search for an entity and return the first Q id that returns
# NB: this feels very imprecise. there's got to be a better way to do this.
def search_for_entity(api_url, query_string):
    uri = api_url + '?action=wbsearchentities&format=json&search=' + urllib.parse.quote(query_string) + '&language=en&type=item&limit=1'
    r = session.get(uri)
    data = r.json()
    if not len(data['search']) == 0:
        entity_id = data['search'][0]['id']
        return entity_id

def read_entity(api_url, entity_id):
    uri = api_url + '?action=wbgetclaims&format=json&entity=' + entity_id
    r = session.get(uri)
    data = r.json()
    claims = data['claims']
    return claims

def create_entity(api_url, edit_token, data_string):
    parameters = {
        'action': 'wbeditentity',
        'format': 'json',
        'new': 'item',
        'token': edit_token,
        # note: the data value is a string. I think it will get URL encoded by requests before posting
        'data': data_string
    }
    r = session.post(api_url, data=parameters)
    response = r.text
    if response[2:7] == 'error':
        return response
    else:
        data = r.json()
        return data["entity"]["id"]

# function for writing statements linking to existing Q items in Wikidata
# pass in the local names including the initial letter as strings, e.g. ('Q3345', 'P6', 'Q1917')
def write_statement_item(api_url, edit_token, subjectQNumber, propertyPNumber, objectQNumber):
    strippedQNumber = objectQNumber[1:len(objectQNumber)] # remove initial "Q" from object string
    parameters = {
        'action':'wbcreateclaim',
        'format':'json',
        'entity':subjectQNumber,
        'snaktype':'value',
        'bot':'1',  # not sure that this actually does anything
        'token': edit_token,
        'property': propertyPNumber,
        # note: the value is a string, not an actual data structure.  I think it will get URL encoded by requests before posting
        'value':'{"entity-type":"item","numeric-id":' + strippedQNumber+ '}'
    }
    r = session.post(api_url, data=parameters)
    data = r.json()
    return data

# function for writing statements where the value is a string
# pass in the local names including the initial letter as strings, e.g. ('Q3345', 'P6', 'Q1917')
def write_statement_string(api_url, edit_token, subjectQNumber, propertyPNumber, string):
    parameters = {
        'action':'wbcreateclaim',
        'format':'json',
        'entity':subjectQNumber,
        'snaktype':'value',
        'bot':'1',  # not sure that this actually does anything
        'token': edit_token,
        'property': propertyPNumber,
        'value': '"' + string + '"'
    }
    r = session.post(api_url, data=parameters)
    data = r.json()
    return data

# function for writing statements where the value is a json string
# pass in the local names including the initial letter as strings, e.g. ('Q3345', 'P6', 'Q1917')
def write_statement_json(api_url, edit_token, subjectQNumber, propertyPNumber, string):
    parameters = {
        'action':'wbcreateclaim',
        'format':'json',
        'entity':subjectQNumber,
        'snaktype':'value',
        'bot':'1',  # not sure that this actually does anything
        'token': edit_token,
        'property': propertyPNumber,
        'value': string
    }
    r = session.post(api_url, data=parameters)
    data = r.json()
    return data

# testing deletion function: unclear to me whether Wikidata entities can be deleted through the API or not
def delete_entity(api_url, edit_token, entity_id):
    parameters = dict(
        action='delete',
        token=edit_token,
        title=entity_id,
        reason='Testing purposes'
    )
    r = session.post(api_url, data=parameters)
    data = r.json()
    return data
