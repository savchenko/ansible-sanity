# ansible-sanity

## About

```
usage: ansible-sanity [-h] [-p PLAYBOOK] [-q]

Sanity-checks between role, its playbooks and readme files.

optional arguments:
  -h, --help            show this help message and exit
  -p PLAYBOOK, --playbook PLAYBOOK
                        Path to the playbook .YML file
  -q, --quiet           Output number of issues only
```

Check if any variable:

1. Declared in playbook and overwriting defaults
1. Declared in playbook, but undeclared in role
1. Declared in role, but absent in playbook
1. Declared in role, but absent in Readme
1. Declared in Readme, but absent in role
1. Declared in Readme, but absent in playbook
1. Has different types in playbook and role

## Performance

It takes ~100ms to parse the [Debian-Playbook](https://github.com/savchenko/debian/tree/bullseye). ~80% of the time spent reading and serialising YAMLs.
