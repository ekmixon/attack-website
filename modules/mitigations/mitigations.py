import json
import os
import urllib3
import re
import markdown
from modules import site_config
from modules import util
from . import mitigations_config

def generate_mitigations():
    """Responsible for verifying mitigation directory and generating index
       mitigation markdown
    """

    # Create content pages directory if does not already exist
    util.buildhelpers.create_content_pages_dir()

    # Move templates to templates directory
    util.buildhelpers.move_templates(mitigations_config.module_name, mitigations_config.mititgations_templates_path)

    # Verify if directory exists
    if not os.path.isdir(mitigations_config.mitigation_markdown_path):
        os.mkdir(mitigations_config.mitigation_markdown_path)

    # Create the mitigation index markdown
    with open(os.path.join(mitigations_config.mitigation_markdown_path, "overview.md"), "w", encoding='utf8') as md_file:
        md_file.write(mitigations_config.mitigation_overview_md)

    # To verify if a technique was generated
    mitigation_generated = False

    mitigations = {}

    ms = util.relationshipgetters.get_ms()

    for domain in site_config.domains:
        if domain['deprecated']: continue
        #Reads the STIX and creates a list of the ATT&CK mitigations
        mitigations[domain['name']] = util.stixhelpers.get_mitigation_list(ms[domain['name']])

    # Amount of characters per category
    group_by = 3

    notes = util.relationshipgetters.get_objects_using_notes()
    side_nav_data = util.buildhelpers.get_side_nav_domains_data("mitigations", mitigations)
    side_nav_mobile_data = util.buildhelpers.get_side_nav_domains_mobile_view_data("mitigations", mitigations, group_by)

    for domain in site_config.domains:
        if domain['deprecated']: continue
        check_if_generated = generate_markdown_files(domain['name'], mitigations[domain['name']], side_nav_data, side_nav_mobile_data, notes)
        if not mitigation_generated and check_if_generated:
            mitigation_generated = True

    if not mitigation_generated:
        util.buildhelpers.remove_module_from_menu(mitigations_config.module_name)   

def generate_markdown_files(domain, mitigations, side_nav_data, side_nav_mobile_data, notes):
    """Responsible for generating shared data between all mitigation pages
       and begins mitigation markdown generation
    """

    if not mitigations:
        return False
    data = {'domain': domain.split("-")[0]}

    data['mitigation_list_len'] = str(len(mitigations))
    data['side_menu_data'] = side_nav_data
    data['side_menu_mobile_view_data'] = side_nav_mobile_data

    data['mitigation_table'] = get_mitigation_table_data(mitigations)

    subs = mitigations_config.mitigation_domain_md.substitute(data)
    subs = subs + json.dumps(data)

    with open(os.path.join(mitigations_config.mitigation_markdown_path, data['domain'] + "-mitigations.md"), "w", encoding='utf8') as md_file:
        md_file.write(subs)

    # Generates the markdown files to be used for page generation
    for mitigation in mitigations:
        generate_mitigation_md(mitigation, domain, side_nav_data, side_nav_mobile_data, notes)

    return True

def generate_mitigation_md(mitigation, domain, side_menu_data, side_menu_mobile_data, notes):
    """Generates the markdown for the given mitigation"""

    if not (attack_id := util.buildhelpers.get_attack_id(mitigation)):
        return
    data = {'attack_id': attack_id, 'domain': domain.split("-")[0]}

    data['side_menu_data'] = side_menu_data
    data['side_menu_mobile_view_data'] = side_menu_mobile_data
    data['name'] = mitigation['name']
    data['notes'] = notes.get(mitigation['id'])

    dates = util.buildhelpers.get_created_and_modified_dates(mitigation)

    if dates.get('created'):
        data['created'] = dates['created']

    if dates.get('modified'):
        data['modified'] = dates['modified']

    # Get initial reference list
    reference_list = {'current_number': 0}

    # Get initial reference list from mitigation object
    reference_list = util.buildhelpers.update_reference_list(reference_list, mitigation)

    if mitigation.get('description'):
        data['descr'] = mitigation['description']
        data['descr'] = data['descr']

    if mitigation.get('x_mitre_deprecated'):
        data['deprecated'] = True
    if mitigation.get('x_mitre_version'):
        data['version'] = mitigation["x_mitre_version"]

    data['techniques_addressed_data'] = get_techniques_addressed_data(mitigation, reference_list)

        # Get navigator layers for this group
    layers = util.buildhelpers.get_navigator_layers(
        data['name'],
        data["attack_id"],
        "mitigation",
        data.get("version", None),
        data['techniques_addressed_data'],
    )


    data["layers"] = []
    for layer in layers:
        with open(os.path.join(mitigations_config.mitigation_markdown_path, "-".join([data['attack_id'], "techniques", layer["domain"]]) + ".md"), "w", encoding='utf8') as layer_json:
            subs = site_config.layer_md.substitute({
                "attack_id": data["attack_id"],
                "path": "mitigations/" + data["attack_id"],
                "domain": layer["domain"]
            })
            subs = subs + layer["layer"]
            layer_json.write(subs)
        data["layers"].append({
            "domain": layer["domain"],
            "filename": "-".join([data["attack_id"], layer["domain"], "layer"]) + ".json",
            "navigator_link" : site_config.navigator_link
        })

    data['citations'] = reference_list

    data['versioning_feature'] = site_config.check_versions_module()

    subs = mitigations_config.mitigation_md.substitute(data)
    subs = subs + json.dumps(data)

    with open(os.path.join(mitigations_config.mitigation_markdown_path, data['attack_id'] + ".md"), "w", encoding='utf8') as md_file:
        md_file.write(subs)

def get_mitigation_table_data(mitigation_list):
    """Given a list of mitigations, returns the data to build
       table on HTML
    """

    mitigation_data = []

    # Fill mitigation data
    for mitigation in mitigation_list:
        if attack_id := util.buildhelpers.get_attack_id(mitigation):
            row = {
                'id': attack_id,
                'name': mitigation['name'],
                'descr': mitigation['description'],
            }


            if mitigation.get('x_mitre_deprecated'):
                row['deprecated'] = True

            mitigation_data.append(row)

    return mitigation_data
    
def get_techniques_addressed_data(mitigation, reference_list):
    """Given a mitigation, returns a list of techniques addressed by 
       the mitigation
    """

    technique_list = {}

    mitigates_techniques = util.relationshipgetters.get_mitigation_mitigates_techniques()

    if mitigates_techniques.get(mitigation['id']): # only if there are techniques for this mitigation
        for technique in mitigates_techniques.get(mitigation['id']):
            # Do not add if technique is deprecated
            if not technique['object'].get('x_mitre_deprecated'):
                technique_list = util.buildhelpers.technique_used_helper(technique_list, technique, reference_list)           

    technique_data = [technique_list[item] for item in technique_list]
    # Sort by technique name
    technique_data = sorted(technique_data, key=lambda k: k['name'].lower())

    # Sort by domain name
    technique_data = sorted(technique_data, key=lambda k: [site_config.custom_alphabet.index(c) for c in k['domain'].lower()])
    return technique_data
