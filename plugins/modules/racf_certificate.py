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
    certificate_owner:
        description: Certificate Owner in RACF if ommitted will be used the user running the playbook
        required: false
        type: str
    distinguished_name:
        description: Certificate Fields
        required: false
        type: dict
        options:
            common_name:  
                description: Common Name field from certificate
                type: str
                required: False
            country: 
                description: Contry field from certificate
                type: str
                required: False
            locality: 
                description: Locality field from certificate
                type: str
                required: False
            organization:
                description: Organization field from certificate
                type: str
                required: False
            organization_unit: 
                description: Organization Unit field from certificate
                type: str
                required: False
            state: 
                description: State/Province field from certificate
                type: str
                required: False
            title: 
                description: Title field from certificate
                type: str
                required: False
            
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

- name: Delete certificate named CertificateLabel from the user running the playbook
  billpereira.community_racf.racf_certificate:
    certificate_label: CertificateLabel
    state: absent

- name: Create a certificate for commonName this will be also the label for the user running the playbook
  billpereira.community_racf.racf_certificate:
    distinguished_name: 
        common_name: commonName
        country: Contry
        locality: Locality
        organization: Organization
        organization_unit: OrganizationUnit
        state: StateProvince
        title: Title
    state: present

- name: Create a certificate for commonName with different label for the certificateOwner
  billpereira.community_racf.racf_certificate:
    distinguished_name: 
        common_name: commonName
    certificate_label: certificateLabel
    certificate_owner: certificateOwner
    state: present


"""

RETURN = r"""
# These are examples of possible return values, and in general should use other names for return values.
  racf_info:
    description:  Th
    sample:
        certificate_id: 2QXB1fDx54KJk5OjoqNA
        common_name: billtst
        end_date: 2025/03/01 23:59:59
        finger_print: 74:A7:50:CF:1A:B0:E5:8E:93:B5:D7:56:11:D6:90:2E:43:E0:39:17:4F:25:0E:D2:CB:18:9D:D9:F8:7B:55:3E
        issuers_name: CN=billtst
        key_size: '2048    '
        key_type: RSA
        label: billtst
        ring_associations:
        - '*** No rings associated ***'
        serial_number: '00'
        start_date: 2024/03/01 00:00:00
        trust: TRUST
        user: USERX
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

def generate_id_owner_suffix(owner):
    return f"ID({owner})" if owner else ""

def generate_label_suffix(label):
    return f"(LABEL(\'{label}\'))" if label else ""

def generate_withlabel_suffix(label):
    return f"WITHLABEL(\'{label}\')" if label else ""

def generate_distinguished_name(distinguished_name):
    cn = f"CN(\'{distinguished_name['common_name']}\') " if distinguished_name['common_name'] else ""
    t = f"CN(\'{distinguished_name['title']}\') " if distinguished_name['title'] else ""
    t = f"T(\'{distinguished_name['title']}\') " if distinguished_name['title'] else ""
    ou = f"OU(\'{distinguished_name['organization_unit']}\') " if distinguished_name['organization_unit'] else ""
    o = f"O(\'{distinguished_name['organization']}\') " if distinguished_name['organization'] else ""
    l = f"L(\'{distinguished_name['locality']}\') " if distinguished_name['locality'] else ""
    c = f"C(\'{distinguished_name['country']}\') " if distinguished_name['country'] else ""
    sp = f"SP(\'{distinguished_name['state']}\') " if distinguished_name['state'] else ""
    return f" SUBJECTSDN({cn}{t}{ou}{o}{l}{c}{sp})"

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
    list_finger_print = re.findall('(?:[0-9A-Fa-f:]{47,48})', list_output)
    list_finger_print_filtered = [ (a, b) for a,b in zip(list_finger_print[::2], list_finger_print[1::2])]
    list_common_name = re.findall('Issuer\'s Name:\W*>CN=(.*?)[<\.]', list_output)
    list_certificates = []
    for index, label in enumerate(list_Label):
        ring_info = []
        if 'No rings' not in list_ring_associations[index]:
            list_output_from_current = run_tso_command_and_capture_output(f"tsocmd \"RACDCERT LIST{generate_label_suffix(list_Label[index])} {generate_id_owner_suffix(user[0])}\"")
            ring_owners = re.findall('Ring Owner:\W*(.*?)\s',list_output_from_current)
            ring_names = re.findall('Ring:\W*\s>(.*)<',list_output_from_current)
            for ring_index, owner in enumerate(ring_owners):
                ring_info.append({
                    'ring_owner': owner,
                    'keyring':ring_names[ring_index]
                })
        else:
            ring_info.append(list_ring_associations[index])
        list_certificates.append({
            'common_name': list_common_name[index],
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
            'ring_associations': ring_info,
            # 'finger_print': ':'.join(list_finger_print[index])
            'finger_print': ''.join(list_finger_print_filtered[index])
        })
    return list_certificates
    # return list_certificates if len(list_certificates)>0 else [list_output]


def list_certificate(certificate_label, certificate_owner):
    list_certificate_command = f"tsocmd \"RACDCERT LIST{generate_label_suffix(certificate_label)} {generate_id_owner_suffix(certificate_owner)}\""
    command_output = run_tso_command_and_capture_output(list_certificate_command)
    results = extract_certificates(command_output)
    return results

def add_certificate(distinguished_name, label, owner):
    add_command = f"tsocmd \"RACDCERT GENCERT {generate_distinguished_name(distinguished_name)} {generate_withlabel_suffix(label)} {generate_id_owner_suffix(owner)}\""
    run_tso_command_and_capture_output(add_command)
    return list_certificate(label,owner)
    # return add_command

def delete_certificate(owner, label):
    delete_command = f"tsocmd \"RACDCERT DELETE{generate_label_suffix(label)} {generate_id_owner_suffix(owner)}\""
    run_tso_command_and_capture_output(delete_command)
    return list_certificate("",owner)

def run_module():
    module_args = dict(
        certificate_owner=dict(type="str", required=False, default=""),
        certificate_label=dict(type="str", required=False,default=""),
        state=dict(
            type="str",
            required=False,
            choices=["present", "absent"],
        ),
        list_only=dict(type="bool", required=False, default=False),
        distinguished_name=dict(type="dict", required=False, default={},options=dict(
            common_name=dict(type="str", required=False,default=""),
            title=dict(type="str", required=False,default=""),
            organization_unit=dict(type="str", required=False,default=""),
            organization=dict(type="str", required=False,default=""),
            locality=dict(type="str", required=False,default=""),
            state=dict(type="str", required=False,default=""),
            country=dict(type="str", required=False,default=""),

            )
        )
    )

    required_if = [
        ("list_only", False, ("state",)),
        ("state","absent",("certificate_owner","certificate_label",),False,),
        ("state","present",("distinguished_name",),False,),
    ]

    result = dict(changed=False, keyring="", racf_info={})
    module = AnsibleModule(
        argument_spec=module_args, supports_check_mode=True, required_if=required_if
    )

    if module.check_mode:
        module.exit_json(**result)

    result["certificate_owner"] = module.params["certificate_owner"]
    result["certificate_label"] = module.params["distinguished_name"]["common_name"] if module.params["certificate_label"] == "" else module.params["certificate_label"]

    result["distinguished_name"] = module.params["distinguished_name"]
    result["list_only"] = module.params["list_only"]

    result["racf_info"] = list_certificate(
        result["certificate_label"], module.params["certificate_owner"]
    )

    if module.params["list_only"]:
        module.exit_json(**result)

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
        result["racf_info"] = delete_certificate(module.params["certificate_owner"], module.params["certificate_label"])
        result["changed"] = True

    if (
        len(result["racf_info"]) == 0
        and module.params["state"] == "present"
    ):
        if module.params["distinguished_name"]["common_name"] == "":
            module.fail_json(msg='Common Name is mandatory for adding new certificate', **result)
        result["racf_info"] = add_certificate(module.params["distinguished_name"], result["certificate_label"],module.params["certificate_owner"] )
        result["changed"] = True

    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
