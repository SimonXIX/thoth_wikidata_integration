# @name: editions.py
# @version: 0.1
# @creation_date: 2021-10-28
# @license: The MIT License <https://opensource.org/licenses/MIT>
# @author: Simon Bowie <ad7588@coventry.ac.uk>
# @purpose: Creates an edition item in Wikidata
# @acknowledgements:
# Wikidata definition of an edition item: https://www.wikidata.org/wiki/Wikidata:WikiProject_Books#Edition_item_properties

import thoth
import wikidata
import json
import re

def create_edition(api_url, CSRF_token, thoth_work, work_id, publication):

    parsed_edition = thoth.parse_thoth_edition(thoth_work, publication)

    # create entity for the edition
    entity_id = wikidata.create_entity(api_url, CSRF_token, parsed_edition)

    # If there's already an entity object with that label and description, return the entity ID of that existing object
    if entity_id[2:7] == 'error':
        data = json.loads(entity_id)
        entity_id_search = re.search("\[\[(Q.*)\|", data["error"]["info"])
        if entity_id_search:
            entity_id = entity_id_search.group(1)

    return entity_id

def write_edition_statements(api_url, CSRF_token, thoth_work, work_id, edition_id, publication):

    # insert statements for the work's various properties
    # first, get the Wikidata property values: these differ between test.wikidata.org and wikidata.org so are set in the config file passed through Docker Compose
    property_values = wikidata.get_property_values()

    # get Wikidata constants such as 'written work'
    wikidata_constants = wikidata.get_constant_entities()

    # check for existing claims on that edition. we'll use this to check whether claim statements already exist for that entity or not.
    existing_claims = wikidata.read_entity(api_url, edition_id)

    sub = edition_id # subject entity

    # insert statement for 'instance of version, edition, or translation'
    if property_values['instance_of'] not in existing_claims:
        prop = property_values['instance_of'] # property
        obj = wikidata_constants['version'] # object entity
        instance_of_response = wikidata.write_statement_item(api_url, CSRF_token, sub, prop, obj)

    # insert statement for 'edition or translation of'
    if property_values['edition_of'] not in existing_claims:
        prop = property_values['edition_of'] # property
        obj = work_id # object entity
        edition_of_response = wikidata.write_statement_item(api_url, CSRF_token, sub, prop, obj)

        # inversely write statement to the work for 'has edition of'
        work = work_id
        prop = property_values['has_edition'] # property
        edition = edition_id # object entity
        #has_edition_response = wikidata.write_statement_item(api_url, CSRF_token, work, prop, edition)

    # insert statement for 'place of publication'
    if property_values['publication_place'] not in existing_claims:
        prop = property_values['publication_place'] # property

        # search for the entity ID for the edition's place of publication
        # NB: this search function feels very imprecise! there's got to be a better way to do this
        obj = wikidata.search_for_entity(api_url, thoth_work['place'].split(',')[0])

        if obj is not None:
            publication_place_response = wikidata.write_statement_item(api_url, CSRF_token, sub, prop, obj)

    # insert statement for 'publisher'
    if property_values['publisher'] not in existing_claims:
        prop = property_values['publisher'] # property
        string = thoth_work['imprint']['publisher']['publisherName']
        publisher_response = wikidata.write_statement_string(api_url, CSRF_token, sub, prop, string)
        #print(publisher_response)

    # insert statement for 'publication date'
    if property_values['publication_date'] not in existing_claims:
        prop = property_values['publication_date'] # property
        publication_date_dict = dict(
            time="+" + thoth_work['publicationDate'] + "T00:00:00Z",
            timezone=0,
            before=0,
            after=0,
            precision=11,
            calendarmodel='http://www.wikidata.org/entity/Q1985727'
        )
        string = json.dumps(publication_date_dict)
        publication_date_response = wikidata.write_statement_json(api_url, CSRF_token, sub, prop, string)

    # insert statement for 'number of pages'
    if property_values['page_count'] not in existing_claims:
        prop = property_values['page_count'] # property
        page_count_dict = dict(
            amount="+" + str(thoth_work['pageCount']),
            unit='1'
        )
        string = json.dumps(page_count_dict)
        page_count_response = wikidata.write_statement_json(api_url, CSRF_token, sub, prop, string)

    # insert statement for 'ISBN-13'
    if property_values['isbn_13'] not in existing_claims:
        prop = property_values['isbn_13'] # property
        string = publication['isbn'] # value string
        #isbn_response = wikidata.write_statement_string(api_url, CSRF_token, sub, prop, string)

    if thoth_work['lccn'] is not None:
        if property_values['lccn'] not in existing_claims:
            # insert statement for 'Library of Congress Control Number'
            prop = property_values['lccn'] # property
            string = thoth_work['lccn']
            lccn_response = wikidata.write_statement_string(api_url, CSRF_token, sub, prop, string)
    else:
        lccn_response = 'No LCCN'

    # insert statement for 'full work available at URL'
    if property_values['url'] not in existing_claims:
        prop = property_values['url'] # property
        string = thoth_work['landingPage'] # value string
        url_response = wikidata.write_statement_string(api_url, CSRF_token, sub, prop, string)

    # insert statement for 'DOI'
    if property_values['doi'] not in existing_claims:
        prop = property_values['doi'] # property
        string = thoth_work['doi'].replace("https://doi.org/","") # value string
        doi_response = wikidata.write_statement_string(api_url, CSRF_token, sub, prop, string)

    # insert statement for 'copyright license'
    if property_values['copyright_license'] not in existing_claims:
        prop = property_values['copyright_license'] # property
        obj = 'Q208934' # object entity
        license_response = wikidata.write_statement_item(api_url, CSRF_token, sub, prop, obj)

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
        elif contributor['contributionType'] == 'TRANSLATOR':
            parsed_person = thoth.parse_person(contributor)
            # create entity for the person
            person_id = wikidata.create_entity(api_url, CSRF_token, parsed_person)
            # If there's already an entity object with that label and description, return the entity ID of that existing object
            if person_id[2:7] == 'error':
                data = json.loads(person_id)
                entity_id_search = re.search("\[\[(Q.*)\|", data["error"]["info"])
                if entity_id_search:
                    person_id = entity_id_search.group(1)
            if property_values['translator'] not in existing_claims:
                prop = property_values['translator']
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

    return edition_id
