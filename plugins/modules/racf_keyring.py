#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
import subprocess
from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type

DOCUMENTATION = r"""
---
module: racf_keyring

short_description: RACF KeyRing Module

version_added: "1.0.0"

description: Ansible module to help manage RACF Keyrings

options:
    name:
        description: Key Ring Name.
        required: true
        type: str
    keyring_owner:
        description: The owner of the keyring, in case it is omitted it will ussume is the same as ansible_user
        required: false
        type: str
    state:
        description:
            - This field is required in case list_only is true
            - If `present` checks if keyring exists if not create
            - If `absent` checks if keyring exists if so deletes 
            - If `connect` it will connect the keyring with certificate data passed through `certificate_owner` and `certificate_label`
            - If `remove` will remove the connection  from keyring with certificate data passed through `certificate_owner` and `certificate_label`
        required: false
        type: str
    certificate_owner:
        description: The owner of certificate that will be connected to the keyring
        required: false
        type: str
    certificate_label:
        description: The label of certificate that will be connected to the keyring
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
- name: Create keyring for the user running playbook
  my_namespace.my_collection.racf_keyring:
    name: keyringName
    state: present 
    
- name: Create keyring for specific user
  my_namespace.my_collection.racf_keyring:
    name: keyringName
    keyring_owner: keyringOwner
    state: present

- name: Delete keyring for the user running playbook
  my_namespace.my_collection.racf_keyring:
    name: keyringName
    state: absent

- name: List the keyringName for the current ansible_user
  my_namespace.my_collection.racf_keyring:
    name: keyringName
    list_only: true
    
- name: Connect the certificateLabel from certificateOwner to the keyringName from keyringOwner
  my_namespace.my_collection.racf_keyring:
    name: keyringName
    keyring_owner: keyringOwner
    certificate_owner: certificateOwner
    certificate_label: certificateLabel
    state: connect
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


def run_tso_command_and_capture_output(command):
    try:
        command_results = subprocess.run([command], capture_output=True, shell=True)
        return command_results.stdout.decode()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error executing TSO command: {e}")

def generate_keyring_owner_suffix(keyring_owner):
    return f"ID({keyring_owner})" if keyring_owner else ""

def extract_certificates(listring):
    cert_info = listring.split("\n")[7:]
    cert_list = [
        {
            "cert_label": entry[2:34].strip(),
            "cert_owner": entry[37:49].strip(),
            "cert_usage": entry[52:61].strip(),
            "cert_default": entry[65:67].strip(),
        }
        for entry in cert_info
        if entry.strip() != ""
    ]
    return cert_list


def list_ring(ringname, keyring_owner):
    keyring_owner_suffix = generate_keyring_owner_suffix(keyring_owner)
    racf_list_command = f"tsocmd 'RACDCERT LISTRING({ringname}) {keyring_owner_suffix}'"
    racf_list_output = run_tso_command_and_capture_output(racf_list_command)
    list_of_certificates = (
        []
        if "No certificates connected" in racf_list_output
        else extract_certificates(racf_list_output)
    )
    return {
        "list_ring": racf_list_command,
        "certificates": list_of_certificates,
        "results": racf_list_output,
    }


def add_ring(ringname, keyring_owner):
    keyring_owner_suffix = generate_keyring_owner_suffix(keyring_owner)
    racf_add_command = f"tsocmd 'RACDCERT ADDRING({ringname}) {keyring_owner_suffix}'"
    run_tso_command_and_capture_output(racf_add_command)


def delete_ring(ringname, keyring_owner):
    keyring_owner_suffix = generate_keyring_owner_suffix(keyring_owner)
    racf_del_command = f"tsocmd 'RACDCERT DELRING({ringname}) {keyring_owner_suffix}'"
    run_tso_command_and_capture_output(racf_del_command)


def connect_certificate(ring_name, keyring_owner, certificate_owner, certificate_label):
    racf_connect_command = f"tsocmd \"RACDCERT CONNECT(id({certificate_owner}) LABEL('{certificate_label}') RING({ring_name})) ID({keyring_owner})\""
    racf_connect_command_output = run_tso_command_and_capture_output(racf_connect_command)
    return racf_connect_command


def remove_certificate(ring_name, keyring_owner, certificate_owner, certificate_label):
    racf_remove_command = f"tsocmd \"RACDCERT REMOVE(id({certificate_owner}) LABEL('{certificate_label}') RING({ring_name})) ID({keyring_owner})\""
    racf_remove_command_output = run_tso_command_and_capture_output(racf_remove_command)
    return racf_remove_command


def run_module():
    module_args = dict(
        name=dict(type="str", required=True),
        keyring_owner=dict(type="str", required=False),
        certificate_owner=dict(type="str", required=False),
        certificate_label=dict(type="str", required=False),
        state=dict(
            type="str",
            required=False,
            choices=["present", "absent", "connect", "remove"],
        ),
        list_only=dict(type="bool", required=False, default=False),
    )

    required_if = [
        ("list_only", False, ("state",)),
        ("state","connect",("keyring_owner","certificate_owner",),False,),
        ("state","connect",("certificate_label","certificate_serial_number",),True,),
        ("state","remove",("keyring_oner", "certificate_owner", "certificate_label"),False,),
    ]

    result = dict(changed=False, keyring="", racf_info={})
    module = AnsibleModule(
        argument_spec=module_args, supports_check_mode=True, required_if=required_if
    )

    if module.check_mode:
        module.exit_json(**result)

    result["keyring_owner"] = module.params["keyring_owner"]
    result["keyring"] = module.params["name"]
    result["list_only"] = module.params["list_only"]

    result["racf_info"] = list_ring(
        module.params["name"], module.params["keyring_owner"]
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
