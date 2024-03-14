# Ansible Collection - billpereira.community_racf

This collection intends to be maintained by the community. To enable manage
RACF functions from Ansible.


## Requirements

Python needs to be installed on the target LPAR

RACF authorization for the user executing the module:
``` 
racf_keyring:

racf_certificate:

racf_user:

To use the CONNECT state, you must have at least one of the following:
The SPECIAL attribute
The group-SPECIAL attribute in the group
The ownership of the group
JOIN or CONNECT authority in the group.
You cannot give a user a higher level of authority in the group than you have.

``` 


## RACF Keyring
