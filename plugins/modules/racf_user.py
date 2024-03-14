#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
# import subprocess
from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type

DOCUMENTATION = r"""
---
module: racf_user

short_description: RACF User Module

version_added: "1.0.0"

description: Ansible module to help manage RACF Users

options:
    name:
        description: The user name in RACF
        required: True
        type: str
    user_name_info: 
        description: Specifies the user name to be associated with the new user ID. You can use a maximum of 20 alphanumeric or non-alphanumeric character
        required: False
        type: str
    user_owner:
        description: Specifies a RACF-defined user or group to be assigned as the owner of the RACF profile for the user being added
        required: False
        type: str
    default_group:
        description: Specifies the name of a RACF-defined group to be used as the default group for the user
        required: False
        type: str
    segments:
        description: List of segments you would like the module to collect info CICS CSDATA DCE DFP EIM KERB LANGUAGE LNOTES NDS NETVIEW NORACF OMVS OPERPARM OVM PROXY TSO WORKATTR
        required: False
        type: list
    groups:
        description: List of Groups to update connection for the user
        required: False
        type: dict
    list_only:
        description: When true module will only execute a list to the user
        required: false
        type: bool
    return_output:
        description: When true will return the ful output of LISTUSER
        required: false
        type: bool
    state:
        description:
            - This field is required in case list_only is true
            - If `present` checks if user exists if not create
            - If `absent` checks if user exists if so deletes 
            - If `connect` it will connect the user with groups specified
            - If `remove` will remove the connection  from user with group
        required: false
        type: str



author:
    - Bill Pereira (@billpereira)
"""

EXAMPLES = r"""
# Pass in a message
- name: List the RACF User
  billpereira.community_racf.racf_user:
    name: RACFUser
    list_only: true

- name: Display TSO USER from source variable
    racf_user:
    name: "{{ source_user }}"
    list_only: true
    segments:
        - dfp
        - tso
        - omvs
        - cics
        - csdata
    register: model_user

- name: Creating {{target_user}} User from {{source_user}}
    racf_user:
    name: "{{target_user}}"
    user_name_info: Automation USERID"
    user_owner: "{{model_user['racf_info'][0]['user_owner']}}"
    default_group: "{{ model_user['racf_info'][0]['user_default_group'] }}"
    state: present

- name: Deleting {{target_user}} user
    racf_user:
    name: "{{target_user}}"
    state: absent
"""

RETURN = r"""
# These are examples of possible return values, and in general should use other names for return values.
  racf_info:
    description:  The RACF User information
    sample:
        raw_output: COMMAND OUTPUT
        user_cics_segment:  list
        user_csdata_segment: list 
        user_default_group: OWNGP
        user_dfp_segment:  list
        user_group_connects: list 
        group_auth: USE
        group_connect_attribute: NONE
        group_owner: OWNER
        user_name_info: UNKNOWN
        user_omvs_segment:  list
        user_owner: ONWER
        user_tso_segment:  list

"""

import subprocess
import re 

# from ..module_utils.racf_helper import generate_keyring_owner_suffix, run_tso_command_and_capture_output

def run_tso_command_and_capture_output(command):
    try:
        command_results = subprocess.run([command], capture_output=True, shell=True)
        return command_results.stdout.decode()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error executing TSO command: {e}")

def extract_user_info(list_output):
    user_name = re.findall('NAME=(.*?)OWNER',list_output)
    user_owner = re.findall('OWNER=(.*?)\s',list_output)
    user_default_group = re.findall('DEFAULT-GROUP=(.*?)\s',list_output)
    user_connects = [{'group_name':item[0].strip(), 'group_auth': item[1].strip(), 'group_owner': item[2].strip(), 'group_attribute': item[3].strip() } for item in re.findall('\sGROUP=(.*?)\s*AUTH=(.*?)\s*CONNECT-OWNER=(.*?)\s[\s\S]*?ATTRIBUTES=(.*?)\s',list_output)]
    try:
        user_csdata_segment = [{key.strip(): value.strip()} for line in list_output.split('CSDATA')[1].splitlines() if "=" in line for key, value in [line.split("=")]]
    except IndexError: 
        user_csdata_segment = []
    user_tso_segment = [{'acctnum':item[0].strip(), 'dest':item[1].strip(), 'holdclass':item[2].strip(),'msgclass':item[3].strip(),'proc':item[4].strip(),'size':item[5].strip(),'maxsize':item[6].strip(),'sysoutclass':item[7].strip(),'userdata':item[8].strip(),'command':item[9].strip()} for item in re.findall('TSO INF[\s\S]*ACCTNUM= (.*)\s*DEST= (.*)\s*HOLDCLASS= (.*)\s*MSGCLASS= (.*)\s*PROC= (.*)\s*SIZE= (.*)\s*MAXSIZE= (.*)\s*SYSOUTCLASS= (.*)\s*USERDATA= (.*)\s*COMMAND=(.*)',list_output)]
    user_cics_segment = [{'opident': item[0].strip(), 'opprty': item[1].strip(), 'timeout': item[2].strip(), 'xrfsoff': item[3].strip()} for item in re.findall('CICS IN[\s\S]*OPIDENT=(.*)\s*OPPRTY= (.*)\s*TIMEOUT= (.*)\s*XRFSOFF= (.*)',list_output)]
    user_dfp_segment = [{'mgmtclass':item[0].strip(), 'storclass':item[1].strip()} for item in re.findall('DFP INF[\s\S]*MGMTCLAS= (.*)\s*STORCLAS= (.*)',list_output)]
    user_omvs_segment = [{'uid':item[0].strip(),'home':item[1].strip(),'program':item[2].strip(),'cputimemax':item[3].strip(),'assizemax':item[4].strip(),'fileprocmax':item[5].strip(),'procusermax':item[6].strip(),'threadsmax':item[7].strip(),'mmapareamax':item[8].strip()} for item in re.findall('OMVS INF[\s\S]*UID= (.*)\s*HOME= (.*)\s*PROGRAM= (.*)\s*CPUTIMEMAX= (.*)\s*ASSIZEMAX= (.*)\s*FILEPROCMAX= (.*)\s*PROCUSERMAX=(.*)\s*THREADSMAX= (.*)\s*MMAPAREAMAX= (.*)',list_output)]
    list_user_info = []
    if 'UNABLE' in list_output: 
        return list_user_info
    list_user_info.append({
        'user_name_info': user_name[0].strip(),
        'user_default_group': user_default_group[0].strip(),
        'user_owner': user_owner[0].strip(),
        'user_group_connects': user_connects,
        'user_tso_segment': user_tso_segment,
        'user_csdata_segment': user_csdata_segment,
        'user_cics_segment': user_cics_segment,
        'user_dfp_segment': user_dfp_segment,
        'user_omvs_segment': user_omvs_segment,
        'raw_output': list_output
    })
    return list_user_info
    # return list_certificates if len(list_certificates)>0 else [list_output]


def list_user(user, segments=''):
    list_user_command = f"tsocmd \"LU {user} {' '.join(segments)}\""
    command_output = run_tso_command_and_capture_output(list_user_command)
    results = extract_user_info(command_output)
    return results

def delete_user(user):
    del_user_command = f"tsocmd \"du {user}\""
    command_output = run_tso_command_and_capture_output(del_user_command)
    results = list_user(user)
    return command_output

def generate_default_group_suffix(default_group):
    return f" DFLTGRP({default_group})" if default_group else ""

def generate_name_suffix(name):
    return f" NAME(\'{name}\')" if name else ""

def generate_owner_suffix(OWNER):
    return f" OWNER({OWNER})" if OWNER else ""

def add_user(user, user_name_info,default_group,user_owner):
    add_user_command = f"tsocmd \"AU {user}{generate_default_group_suffix(default_group)}{generate_name_suffix(user_name_info)}{generate_owner_suffix(user_owner)}\""
    command_output = run_tso_command_and_capture_output(add_user_command)
    results = list_user(user)
    return results if len(results)>0 else command_output

def connect_groups(user, groups, user_group_connects):
    group_updated = False
    missing_groups = []
    connect_results = []
    for group in groups:
        found_match = next((item for item in user_group_connects if item.get('group') == group['group_name']), None)
        if found_match is None:
            missing_groups.append(group)
            connect_command = f"tsocmd \"CO ({user}) GROUP({group['group_name']})\""
            connect_results.append(run_tso_command_and_capture_output(connect_command))
            group_updated = True
    results = list_user(user)
        
            
    return {
        'updated_groups': missing_groups,
        'updated_user': results,
        'command_outputs': connect_results,
        'user_changed': group_updated
    }


def run_module():
    module_args = dict(
        name=dict(type="str", required=True),
        segments=dict(type="list",required=False, default=[]),
        default_group=dict(type="str",required=False,default=''),
        user_name_info=dict(type="str",required=False,default=''),
        user_owner=dict(type='str',required=False,default=''),
        groups=dict(type="list",required=False, default=[],elements='dict',options=dict(
            group_name=dict(type="str",required=False, default=''),
            group_auth=dict(type="str",required=False, default=''),
            group_attribute=dict(type="str",required=False, default=''),
            group_owner=dict(type="str",required=False, default=''),
        )),
        state=dict(
            type="str",
            required=False,
            choices=["present", "absent", "connect","remove"],
        ),
        list_only=dict(type="bool", required=False, default=False),
        return_output=dict(type="bool", required=False, default=False),
    )

    required_if = [
        ("list_only", False, ("state",)),
    ]

    result = dict(changed=False, racf_info={})
    module = AnsibleModule(
        argument_spec=module_args, supports_check_mode=True, required_if=required_if
    )
    if module.check_mode:
        module.exit_json(**result)

    result["name"] = module.params["name"]
    result["list_only"] = module.params["list_only"]

    result["racf_info"] = list_user(
        result["name"], module.params["segments"],
    )

    if module.params["list_only"]:
        module.exit_json(**result)

    if module.params['state'] == 'connect':
        if len(result['racf_info']) == 0:
            module.fail_json(msg=f"Unable to find {module.params['name']} to perform connect", **result)
        connect_results = connect_groups(module.params['name'], module.params['groups'], result['racf_info'][0]['user_group_connects'])
        result['updated_group_connections'] = connect_results['updated_groups']
        result['connect_outputs'] = connect_results['command_outputs']
        result["changed"] = connect_results['user_changed']
        result['racf_info'] = connect_results['updated_user']

    if (
        len(result["racf_info"]) == 0
        and module.params["state"] == "absent"
    ) or (
        len(result["racf_info"]) == 1
        and module.params["state"] == "present"
    ):
        result["changed"] = False
        module.exit_json(**result)

    if (
        len(result["racf_info"]) == 1
        and module.params["state"] == "absent"
    ):
        result["racf_info"] = delete_user(module.params["name"])
        result["changed"] = True

    if (
        len(result["racf_info"]) == 0
        and module.params["state"] == "present"
    ):
        result["racf_info"] = add_user(module.params["name"], module.params['user_name_info'],module.params['default_group'],module.params['user_owner'])
        result["changed"] = True

    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
