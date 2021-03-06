# @name: work.py
# @version: 0.1
# @creation_date: 2021-10-28
# @license: The MIT License <https://opensource.org/licenses/MIT>
# @author: Simon Bowie <ad7588@coventry.ac.uk>
# @purpose: Creates a work item in Wikidata (https://www.wikidata.org/wiki/Wikidata:WikiProject_Books#Work_item_properties)
# @acknowledgements:
# Wikidata definition of a work item: https://www.wikidata.org/wiki/Wikidata:WikiProject_Books#Work_item_properties

import thoth
import wikidata
import json
import re

def create_work(api_url, CSRF_token, thoth_work):
    parsed_work = thoth.parse_thoth_work(thoth_work)

    # create entity for the work
    entity_id = wikidata.create_entity(api_url, CSRF_token, parsed_work)

    # If there's already an entity object with that label and description, return the entity ID of that existing object
    if entity_id[2:7] == 'error':
        data = json.loads(entity_id)
        entity_id_search = re.search("\[\[(Q.*)\|", data["error"]["info"])
        if entity_id_search:
            entity_id = entity_id_search.group(1)

    return entity_id

def write_work_statements(api_url, CSRF_token, thoth_work, work_id):

    # insert statements for the work's various properties
    # first, get the Wikidata property values: these differ between test.wikidata.org and wikidata.org so are set in the config file passed through Docker Compose
    property_values = wikidata.get_property_values()

    # get Wikidata constants such as 'written work'
    wikidata_constants = wikidata.get_constant_entities()

    # check for existing claims on that work. we'll use this to check whether claim statements already exist for that entity or not.
    existing_claims = wikidata.read_entity(api_url, work_id)

    sub = work_id # subject entity

    # insert statement for 'instance of written work'
    if property_values['instance_of'] not in existing_claims:
        prop = property_values['instance_of'] # property
        obj = wikidata_constants['written_work'] # object entity
        instance_of_response = wikidata.write_statement_item(api_url, CSRF_token, sub, prop, obj)

    # insert statement for 'title'
    if property_values['title'] not in existing_claims:
        prop = property_values['title'] # property
        title_dict = dict(
            text=thoth_work['title'],
            language='en'
        )
        string = json.dumps(title_dict)
        title_response = wikidata.write_statement_json(api_url, CSRF_token, sub, prop, string)

    # insert statement for 'subtitle'
    if thoth_work['subtitle'] is not None:
        if property_values['subtitle'] not in existing_claims:
            # insert statement for 'subtitle'
            prop = property_values['subtitle'] # property
            string = thoth_work['subtitle']
            subtitle_response = wikidata.write_statement_string(api_url, CSRF_token, sub, prop, string)
    else:
        subtitle_response = 'No subtitle'

    # insert statement for 'author', 'editor', 'translator', or 'contributor'
    for contributor in thoth_work['contributions']:
        if contributor['contributionType'] == 'AUTHOR':
            parsed_person = thoth.parse_person(contributor)
            # create entity for the person
            person_id = wikidata.create_entity(api_url, CSRF_token, parsed_person)
            # If there's already an entity object with that label and description, return the entity ID of that existing object
            if person_id[2:7] == 'error':
                data = json.loads(person_id)
                entity_id_search = re.search("\[\[(Q.*)\|", data["error"]["info"])
                if entity_id_search:
                    person_id = entity_id_search.group(1)
            if property_values['author'] not in existing_claims:
                prop = property_values['author']
                obj = person_id
                author_response = wikidata.write_statement_item(api_url, CSRF_token, sub, prop, obj)
        elif contributor['contributionType'] == 'EDITOR':
            parsed_person = thoth.parse_person(contributor)
            # create entity for the person
            person_id = wikidata.create_entity(api_url, CSRF_token, parsed_person)
            # If there's already an entity object with that label and description, return the entity ID of that existing object
            if person_id[2:7] == 'error':
                data = json.loads(person_id)
                entity_id_search = re.search("\[\[(Q.*)\|", data["error"]["info"])
                if entity_id_search:
                    person_id = entity_id_search.group(1)
            if property_values['editor'] not in existing_claims:
                prop = property_values['editor']
                obj = person_id
                editor_response = wikidata.write_statement_item(api_url, CSRF_token, sub, prop, obj)
        else:
            parsed_person = thoth.parse_person(contributor)
            # create entity for the person
            person_id = wikidata.create_entity(api_url, CSRF_token, parsed_person)
            # If there's already an entity object with that label and description, return the entity ID of that existing object
            if person_id[2:7] == 'error':
                data = json.loads(person_id)
                entity_id_search = re.search("\[\[(Q.*)\|", data["error"]["info"])
                if entity_id_search:
                    person_id = entity_id_search.group(1)
            if property_values['contributor'] not in existing_claims:
                prop = property_values['contributor']
                obj = person_id
                contributor_response = wikidata.write_statement_item(api_url, CSRF_token, sub, prop, obj)

    # insert statement for 'main subject'
    for subject in thoth_work['subjects']:
        if subject['subjectType'] == 'KEYWORD' and subject['subjectOrdinal'] == 1:
            print(subject['subjectCode'])

    return work_id
