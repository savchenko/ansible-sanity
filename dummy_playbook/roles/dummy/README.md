# Dummy

Test role to use with the Ansible-sanity.

## Requirements

- Ansible ≥2.10
- ansible-sanity

## Role Variables

| Variable                                    | Description                               | Default                                                                 |
|---------------------------------------------|-------------------------------------------|-------------------------------------------------------------------------|
| integer                                     |                                           | 42                                                                      |
| float                                       |                                           | 19.1459                                                                 |
| string_single                               |                                           | 'Single-quoted string'                                                  |
| string_double                               |                                           | "Double-quoted string"                                                  |
| string_single_empty                         |                                           | ''                                                                      |
| string_double_empty                         |                                           | ""                                                                      |
| string_single_unicode                       |                                           | '±¶µ»½'                                                                 |
| string_double_unicode                       |                                           | "±¶µ»½"                                                                 |
| bool_capitalised                            |                                           | True                                                                    |
| bool_lowercase                              |                                           | true                                                                    |
| bool_uppercase                              |                                           | TRUE                                                                    |
| bool_mixed                                  |                                           | tRuE                                                                    |
| list_empty                                  |                                           | []                                                                      |
| list_nonempty                               |                                           | ['elem_A', 'elem_B', 'elem_C']                                          |
| list_nested                                 |                                           | ['elem_A-top', ['elem_B-nested', 'elem_C-nested']]                      |
| list_multiline                              | In multiline form.                        | ['One', 1, 1.0]                                                         |
| dictionary_empty                            |                                           | {}                                                                      |
| dictionary_nonempty                         |                                           | {'key': 'value'}                                                        |
| dictionary_nested                           | In multiline form.                        | {'top_key': {'nested_key': {'nested_value': {'another': 'dictionary'}}} |
| e_overwrites_defaults                       | Declared in playbook, overwrites defaults | true                                                                    |
| e_declared_in_playbook_underclared_in_role  | Declared in playbook, undeclared in role  | true                                                                    |
| e_declared_in_role_undeclared_in_playbook   | Declared in role, absent in playbook      | true                                                                    |
| e_declared_in_readme_undeclared_in_role     | Declared in Readme, absent in role        | true                                                                    |
| e_declared_in_readme_undeclared_in_playbook | Declared in Readme, absent in playbook    | true                                                                    |
| e_type_mismatch                             | Type mismatch between playbook and role   | true                                                                    |

## Dependencies

None.

## License

Apache-2.0

## Author Information

Andrew Savchenko\
https://savchenko.net
