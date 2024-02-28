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
    name:
        description: Key Ring Name.
        required: true
        type: str


author:
    - Bill Pereira (@billpereira)
"""

EXAMPLES = r"""
# Pass in a message
- name: Create keyring for the user running playbook
  my_namespace.my_collection.racf_keyring:
    name: keyringName
    state: present 

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

from ..module_utils.racf_helper import generate_keyring_owner_suffix, run_tso_command_and_capture_output

# def run_tso_command_and_capture_output(command):
#     try:
#         command_results = subprocess.run([command], capture_output=True, shell=True)
#         return command_results.stdout.decode()
#     except subprocess.CalledProcessError as e:
#         raise RuntimeError(f"Error executing TSO command: {e}")

# def generate_keyring_owner_suffix(keyring_owner):
#     return f"ID({keyring_owner})" if keyring_owner else ""

def list_certificate():
    return

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
