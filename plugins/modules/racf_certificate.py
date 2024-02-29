#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
# import subprocess
from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type

DOCUMENTATION = r"""
---
module: racf_keyring

short_description: RACF Certiifcate Module

version_added: "1.0.0"

description: Ansible module to help manage RACF Certificates

options:
    certificate_label:
        description: The label of certificate in RACF
        required: false
        type: str
    list_only:
        description: When true module will only execute a list to the keyring
        required: false
        type: bool



author:
    - Bill Pereira (@billpereira)
"""

EXAMPLES = r"""
# Pass in a message
- name: List all certificates from user running the playbook
  billpereira.community_racf.racf_certificate:
    list_only: true

- name: List certificates with label parm from user running the playbook
  billpereira.community_racf.racf_certificate:
    certificate_label: CertificateLabel
    list_only: true

"""

RETURN = r"""
# These are examples of possible return values, and in general should use other names for return values.
  racf_info:
    description: The RACF info about the keyring after module execution
    sample:
        certificates: list of certificates
        list_ring: command used to list the keyring
        results: Result of display
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

def generate_id_owner_suffix(keyring_owner):
    return f"ID({keyring_owner})" if keyring_owner else ""

def generate_label_suffix(common_name):
    return f"(LABEL(\'{common_name}\'))" if common_name else ""

def extract_certificates(list_output):
    user = re.findall('for user (.*):',list_output)
    list_Label = re.findall('Label:\s(.*)\n',list_output)
    list_Certificate_ID = re.findall('Certificate ID:\s(.*)\n',list_output)
    list_Issuers_Name = re.findall('Issuer\'s Name:\W*\s>(.*)<',list_output)
    list_start_date = re.findall('Start Date:\W*(.*)\n',list_output)
    list_end_date = re.findall('End Date:\W*(.*)\n',list_output)
    list_trust_status =  re.findall('Status:\W*(.*)\n',list_output)
    list_key_type =  re.findall('Key Type:\W*(.*)\n',list_output)
    list_key_size =  re.findall('Key Size:\W*(.*)\n',list_output)
    list_serial_number = re.findall('Serial Number:\W*>(.*)<',list_output)
    list_ring_associations = re.findall('Ring Associations:\s*(.*)\W*', list_output)
    list_certificates = []
    for index, label in enumerate(list_Label):
        ring_info = []
        if 'No rings' not in list_ring_associations[index]:
            list_output_from_current = run_tso_command_and_capture_output(f"tsocmd \"RACDCERT LIST{generate_label_suffix(list_Label[index])} {generate_id_owner_suffix(user[0])}\"")
            ring_owners = re.findall('Ring Owner:\W*(.*?)\s',list_output_from_current)
            ring_names = re.findall('Ring:\W*\s>(.*)<',list_output_from_current)
            # ring_info.append(f"tsocmd \"RACDCERT LIST{generate_label_suffix(list_Label[index])} {generate_id_owner_suffix(user)}\"")
            for ring_index, owner in enumerate(ring_owners):
                ring_info.append({
                    'ring_owner': owner,
                    'keyring':ring_names[ring_index]
                })
        else:
            ring_info.append(list_ring_associations[index])
        list_certificates.append({
            'user':user[0],
            'label':list_Label[index],
            'certificate_id':list_Certificate_ID[index],
            'issuers_name': list_Issuers_Name[index],
            'start_date': list_start_date[index],
            'end_date': list_end_date[index],
            'trust': list_trust_status[index],
            'key_type': list_key_type[index],
            'key_size': list_key_size[index],
            'serial_number': list_serial_number[index],
            'ring_associations': ring_info
        })
    return list_certificates if len(list_certificates)>0 else [list_output]


def list_certificate(certificate_label, certificate_owner):
    list_certificate_command = f"tsocmd \"RACDCERT LIST{generate_label_suffix(certificate_label)} {generate_id_owner_suffix(certificate_owner)}\""
    command_output = run_tso_command_and_capture_output(list_certificate_command)
    results = extract_certificates(command_output)
    return results

def create_new_certificate():
    return

def run_module():
    module_args = dict(
        certificate_owner=dict(type="str", required=False, default=""),
        common_name=dict(type="str", required=False, default=""),
        certificate_label=dict(type="str", required=False),
        state=dict(
            type="str",
            required=False,
            choices=["present", "absent"],
        ),
        list_only=dict(type="bool", required=False, default=False),
    )

    required_if = [
        ("list_only", False, ("state","certificate_label")),
        ("state","absent",("certificate_owner","certificate_label",),False,),
        ("state","present",("common_name",),False,),
    ]

    result = dict(changed=False, keyring="", racf_info={})
    module = AnsibleModule(
        argument_spec=module_args, supports_check_mode=True, required_if=required_if
    )

    if module.check_mode:
        module.exit_json(**result)

    result["common_name"] = module.params["common_name"]
    result["certificate_owner"] = module.params["certificate_owner"]
    result["certificate_label"] = module.params["certificate_label"]
    result["list_only"] = module.params["list_only"]

    result["racf_info"] = list_certificate(
        module.params["certificate_label"], module.params["certificate_owner"]
    )

    if module.params["list_only"]:
        module.exit_json(**result)

    if (
        "does not exist" in result["racf_info"]["results"]
        and module.params["state"] == "absent"
    ) or (
        "does not exist" not in result["racf_info"]["results"]
        and module.params["state"] == "present"
    ):
        result["changed"] = False
        module.exit_json(**result)

    if (
        "does not exist" in result["racf_info"]["results"]
        and module.params["state"] == "present"
    ):
        add_ring(module.params["name"], module.params["keyring_owner"])
        result["changed"] = True
        result["racf_info"] = list_ring(
            module.params["name"], module.params["keyring_owner"]
        )

    if (
        "does not exist" not in result["racf_info"]["results"]
        and module.params["state"] == "absent"
    ):
        delete_ring(module.params["name"], module.params["keyring_owner"])
        result["changed"] = True
        result["racf_info"] = list_ring(
            module.params["name"], module.params["keyring_owner"]
        )

    if (
        "does not exist" not in result["racf_info"]["results"]
        and module.params["state"] == "present"
    ):
        result["results"] = result["racf_info"]

    if module.params["state"] == "connect":
        result["changed"] = (
            False
            if module.params["certificate_label"] in result["racf_info"]["results"]
            else True
        )
        result["connect_command"] = connect_certificate(
            module.params["name"],
            module.params["keyring_owner"],
            module.params["certificate_owner"],
            module.params["certificate_label"],
        )
        result["racf_info"] = list_ring(
            module.params["name"], module.params["keyring_owner"]
        )

    if module.params["state"] == "remove":
        result["changed"] = (
            False
            if module.params["certificate_label"] not in result["racf_info"]["results"]
            else True
        )
        result["remove_command"] = remove_certificate(
            module.params["name"],
            module.params["keyring_owner"],
            module.params["certificate_owner"],
            module.params["certificate_label"],
        )
        result["racf_info"] = list_ring(
            module.params["name"], module.params["keyring_owner"]
        )

    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
