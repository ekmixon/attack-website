import os
import json
import collections
import re
import markdown
from .. import site_config
from . import datasources_config
from modules import util
from modules.util import relationshipgetters as rsg

def generate_datasources():
    """Responsible for verifying data source directory and starting off 
       data source markdown generation
    """

    # Create content pages directory if does not already exist
    util.buildhelpers.create_content_pages_dir()
    
    # Move templates to templates directory
    util.buildhelpers.move_templates(datasources_config.module_name_no_spaces, datasources_config.datasources_templates_path)

    # Create content pages directory if does not already exist
    util.buildhelpers.create_content_pages_dir()

    # Verify if directory exists
    if not os.path.isdir(datasources_config.datasource_markdown_path):
        os.mkdir(datasources_config.datasource_markdown_path)

    # Generates the markdown files to be used for page generation
    datasource_generated = generate_markdown_files()

    if not datasource_generated:
        util.buildhelpers.remove_module_from_menu(datasources_config.module_name_no_spaces)

def generate_markdown_files():
    """Responsible for generating datasource index page and getting shared data for
       all datasources
    """

    datasource_list = rsg.get_datasource_list()
    datasource_list_no_deprecated_revoked = util.buildhelpers.filter_deprecated_revoked(datasource_list)

    has_datasource = bool(datasource_list_no_deprecated_revoked)
    if has_datasource:
        # Amount of characters per category
        group_by = 2

        notes = rsg.get_objects_using_notes()
        side_menu_data = get_datasources_side_nav_data(datasource_list_no_deprecated_revoked)
        data = {'side_menu_data': side_menu_data}
        side_menu_mobile_view_data = util.buildhelpers.get_side_menu_mobile_view_data(datasources_config.module_name, "/datasources/", datasource_list_no_deprecated_revoked, group_by)
        data['side_menu_mobile_view_data'] = side_menu_mobile_view_data

        data['datasources_table'] = get_datasources_table_data(datasource_list_no_deprecated_revoked)
        data['datasources_list_len'] = str(len(datasource_list_no_deprecated_revoked))

        subs = datasources_config.datasource_index_md + json.dumps(data)

        with open(os.path.join(datasources_config.datasource_markdown_path, "overview.md"), "w", encoding='utf8') as md_file:
            md_file.write(subs)

        #Create the markdown for the enterprise datasources in the STIX
        for datasource in datasource_list:
            generate_datasource_md(datasource, side_menu_data, side_menu_mobile_view_data, notes)

    return has_datasource

def generate_datasource_md(datasource, side_menu_data, side_menu_mobile_view_data, notes):
    """Responsible for generating markdown of all datasources"""

    if not (attack_id := util.buildhelpers.get_attack_id(datasource)):
        return
    data = {
        'attack_id': attack_id,
        'side_menu_data': side_menu_data,
        'side_menu_mobile_view_data': side_menu_mobile_view_data,
        'notes': notes.get(datasource['id']),
    }


    # Get initial reference list
    reference_list = {'current_number': 0}

    # Get initial reference list from group object
    reference_list = util.buildhelpers.update_reference_list(reference_list, datasource)

    dates = util.buildhelpers.get_created_and_modified_dates(datasource)

    if dates.get('created'):
        data['created'] = dates['created']

    if dates.get('modified'):
        data['modified'] = dates['modified']

    if datasource.get("name"):
        data['name'] = datasource['name']

    if datasource.get("x_mitre_version"):
        data['version'] = datasource["x_mitre_version"]

    if isinstance(datasource.get("x_mitre_contributors"),collections.Iterable):
        data['contributors_list'] = datasource["x_mitre_contributors"]

    if datasource.get("description"):
        data['descr'] = datasource['description']

    if datasource.get("x_mitre_platforms"):
        datasource['x_mitre_platforms'].sort()
        data['platforms'] = ", ".join(datasource['x_mitre_platforms'])

    if datasource.get("x_mitre_collection_layers"):
        datasource['x_mitre_collection_layers'].sort()
        data['collection_layers'] = ", ".join(datasource['x_mitre_collection_layers'])

    # Get data components of data source and the technique relationships
    data['datacomponents_list'] = get_datacomponents_data(datasource, reference_list)

    data['citations'] = reference_list

    if datasource.get('x_mitre_deprecated'):
        data['deprecated'] = True

    data['versioning_feature'] = site_config.check_versions_module()

    datasource_data_md = datasources_config.datasource_md.substitute(data)
    datasource_data_md = datasource_data_md + json.dumps(data)

    # Write out the markdown file
    with open(os.path.join(datasources_config.datasource_markdown_path, data['attack_id'] + ".md"), "w", encoding='utf8') as md_file:
        md_file.write(datasource_data_md)

def get_datasources_side_nav_data(datasources):
    """Responsible for generating the links that are located on the
       left side of individual data sources domain pages
    """

    side_nav_data = []

    # Get data components of data source
    datacomponent_of = rsg.get_datacomponent_of()

    for datasource in datasources:

        if attack_id := util.buildhelpers.get_attack_id(datasource):
            datasource_data = {
                "name": datasource['name'],
                "id": attack_id,
                "path": f"/datasources/{attack_id}/",
                "children": [],
            }


            if datacomponent_of.get(datasource['id']):
                for datacomponent in datacomponent_of[datasource['id']]:

                    if not datacomponent.get('x_mitre_deprecated') and not datacomponent.get('revoked'):
                        datacomponent_data = {
                            "name": datacomponent['name'],
                            "id": datacomponent['name'],
                            "path": f"/datasources/{attack_id}/#{datacomponent['name']}",
                            "children": [],
                        }


                        # Add data component data to data source
                        datasource_data['children'].append(datacomponent_data)

                    # Sort subtechniques by ATT&CK ID
                    if datasource_data['children']:
                        datasource_data['children'] = sorted(datasource_data['children'], key=lambda k: k['name'].lower())

        # add data source and children to the side navigation
        side_nav_data.append(datasource_data)

    side_nav_data = sorted(side_nav_data, key=lambda k: k['name'].lower())

    return {
        "name": "Data Sources",
        "id": "datasources",
        "path": None, # root level doesn't get a path
        "children": side_nav_data
    }

def get_datasources_table_data(datasource_list):
    """Responsible for generating datasource table data for the datasource index page"""

    datasources_table_data = []

    #Now the table on the right, which is made up of datasource data
    for datasource in datasource_list:

        if attack_id := util.buildhelpers.get_attack_id(datasource):
            row = {'id': attack_id}

            if datasource.get("name"):
                row['name'] = datasource['name']

            if datasource.get("description"):
                row['descr'] = datasource["description"]

                if datasource.get('x_mitre_deprecated'):
                    row['deprecated'] = True

            datasources_table_data.append(row)

    # Sort by data source name
    datasources_table_data = sorted(datasources_table_data, key=lambda k: k['name'].lower())

    return datasources_table_data

def get_datacomponents_data(datasource, reference_list):
    """Given a data source and its reference list, get a list of data components of the
       data source. Add techniques detected by data components. Check the reference list for citations, if not found
       in list, add it.
    """

    datacomponents_data = []

    # Get data components of data source
    datacomponent_of = rsg.get_datacomponent_of()

    if datacomponent_of.get(datasource['id']):
        for datacomponent in datacomponent_of[datasource['id']]:

            if not datacomponent.get('x_mitre_deprecated') and not datacomponent.get('revoked'):
                reference = False

                datacomponent_data = {
                    'name': datacomponent['name'],
                    'descr': datacomponent['description'],
                }

                # Update reference list
                reference_list = util.buildhelpers.update_reference_list(reference_list, datacomponent)

                if techniques_detected_by_datacomponent := rsg.get_techniques_detected_by_datacomponent().get(
                    datacomponent['id']
                ):
                    datacomponent_data['techniques'] = []

                    technique_list = {}
                    for technique_rel in techniques_detected_by_datacomponent:

                        # Do not add if technique is deprecated
                        if not technique_rel['object'].get('x_mitre_deprecated'):
                            technique_list = util.buildhelpers.technique_used_helper(technique_list, technique_rel, reference_list)

                            technique_data = []
                            for item in technique_list:
                                if (
                                    technique_list[item].get('descr')
                                    and reference == False
                                ):
                                    reference = True
                                technique_data.append(technique_list[item])
                            # Sort by technique name
                            technique_data = sorted(technique_data, key=lambda k: k['name'].lower())

                            datacomponent_data['techniques'] = technique_data
                            datacomponent_data['add_datacomponent_ref'] = reference

                datacomponents_data.append(datacomponent_data)

    # Sort output by data component name
    datacomponents_data = sorted(datacomponents_data, key=lambda k: k['name'].lower())

    return datacomponents_data