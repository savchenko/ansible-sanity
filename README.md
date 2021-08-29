# ansible-sanity

```
usage: ansible-sanity [-h] [-p PLAYBOOK] [-c] [-b] [-q]

Sanity-checks between role, its playbooks and readme files.

optional arguments:
  -h, --help            show this help message and exit
  -p PLAYBOOK, --playbook PLAYBOOK
                        Path to the playbook .YML file
  -c, --consistency     Check variables consistency
  -b, --become          Check that `become` has username defined
  -q, --quiet           Output number of issues only
```

Checks if any variable:

1. Declared in playbook and overwriting defaults
1. Declared in playbook, but undeclared in role
1. Declared in role, but absent in playbook
1. Declared in role, but absent in Readme
1. Declared in Readme, but absent in role
1. Declared in Readme, but absent in playbook
1. Has different types in playbook and role

Additionally inspects:

1. If there are `include_role` and `import_role` overlaps
1. `become` and `become_user` issues
1. Empty `name:` tags
1. Duplicated roles

## Performance

It takes ~100ms to parse the [Debian-Playbook](https://github.com/savchenko/debian/tree/bullseye). ~80% of the time spent reading and serialising YAMLs.

# ansible-unifier

```
usage: ansible-unifier [-h] [-d DIR] [-q]

Unifies quotation and booleans in a way that doesn't explode

optional arguments:
  -h, --help         show this help message and exit
  -d DIR, --dir DIR  Path to the ../roles/ directory
  -q, --quiet        Output nothing except of the issues count
```

Makes `.YML` single-quoted where it's safe and converts YAML-isms à la "yes", "yarr", "nay" to well-known "True" or "False".
