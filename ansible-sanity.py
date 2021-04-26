#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Andrew Savchenko (c) Apache 2.0
# andrew@savchenko.net


import yaml
import os
import argparse
from re import match
from itertools import chain


parser = argparse.ArgumentParser(prog='ansible-sanity',
                                 description='Sanity-checks between role, its playbooks and readme files.')
parser.add_argument('-p', '--playbook', help="Path to the playbook .YML file")
parser.add_argument('-q', '--quiet', action='store_true', help="Output number of issues only")
args = parser.parse_args()


if args.playbook and args.playbook.endswith('.yml'):
    if os.path.isfile(args.playbook):
        pbook_dir = os.path.basename(os.path.normpath(args.playbook))
    else:
        raise Exception("ERROR: Unable to open %s" % args.playbook)
else:
    parser.exit(parser.print_usage())


# Variables present in a playbook
pbook_vars = {}

# Variables obtained from vars/defaults YAMLs
collected_vars = {}

# List of YAMLs within ../vars/* and ../defaults/*
files_to_check = {}

# Issues found
issues = {}
issues_count = 0


#
# Open playbook, parse its content
#
with open(args.playbook, 'r') as pbook_yaml:
    pbook_yaml_parsed = yaml.safe_load(pbook_yaml)
    for issue in pbook_yaml_parsed[0]['tasks']:
        pbook_vars[issue['include_role']['name']] = issue['vars']
    pbook_yaml.close()


#
# Collect YAMLs and READMEs
#
for role in pbook_vars:
    role_path = os.path.join(os.path.dirname(os.path.normpath(args.playbook)), 'roles', role)
    files_to_check[role] = []
    for root, dirs, files in os.walk(role_path):
        if 'README.md' in files:
            files_to_check[role].append(os.path.join(root, 'README.md'))
        root_base = os.path.basename(os.path.normpath(root))
        if root_base in ('vars', 'defaults'):
            for f in files:
                files_to_check[role].append(os.path.join(root, f))


#
# Collect variables from default/vars and README.md
#
for role in files_to_check:
    collected_vars[role] = {'vars': [], 'defaults': [], 'readme': []}
    for f in files_to_check[role]:
        if os.path.basename(os.path.abspath(os.path.join(f, os.pardir))) == 'vars':
            f_type = 'vars'
        elif os.path.basename(os.path.abspath(os.path.join(f, os.pardir))) == 'defaults':
            f_type = 'defaults'
        elif os.path.basename(f) == 'README.md':
            f_type = 'readme'
        else:
            raise Exception('ERROR: Unexpected element in %s' % files_to_check[role])
        if f_type != 'readme':
            with open(f, 'r') as f_yaml:
                try:
                    f_yaml_loaded = yaml.safe_load(f_yaml)
                    for var in f_yaml_loaded:
                        collected_vars[role][f_type].append([var, type(f_yaml_loaded[var])])
                except TypeError:
                    print('WARNING: ..' + f.split('roles')[1] + ' has no valid YAML content')
            f_yaml.close()
        else:
            with open(f, 'r') as f_readme:
                f_lines = f_readme.readlines()
                for ln in f_lines:
                    if match("^\|\s+\w+\s+\|\s+.*\|$", ln):
                        if not match("\|\s+Variable\s+\|\s+Description\s+\|\s+Default\s+\|", ln):
                            collected_vars[role][f_type].append(ln.split('|')[1].strip())
            f_readme.close()


#
# Find issues
#
for role in pbook_vars:
    issues[role] = {
        'defaults': [],              # Declared in playbook and overwriting defaults
        'undeclared': [],            # Declared in playbook, but undeclared in the role
        'absent': [],                # Declared in role, but absent in playbook
        'readme_not-in-readme': [],  # Declared in role, but absent in Readme
        'readme_not-in-role': [],    # Declared in Readme, but absent in role
        'readme_not-in-pbook': [],   # Declared in Readme, but absent in playbook
        'type_mismatch': []          # Type mismatch between the playbook and role
    }
    role_var_names = [x[0] for x in collected_vars[role]['vars']]
    for var in pbook_vars[role]:
        # Declared in playbook, but undeclared in the role
        if var not in role_var_names and var not in collected_vars[role]['defaults']:
            issues[role]['undeclared'].append(var)
        # Declared in playbook and overwriting defaults
        if var in collected_vars[role]['defaults']:
            issues[role]['defaults'].append(var)
        # Type mismatch between the playbook and role
        for cvar in collected_vars[role]['vars']:
            if cvar[0] == var:
                if type(pbook_vars[role][var]) != cvar[1]:
                    issues[role]['type_mismatch'].append(cvar[0])
    for var in role_var_names:
        # Declared in role, but absent in playbook
        if var not in pbook_vars[role]:
            issues[role]['absent'].append(var)
        # Declared in role, but absent in Readme
        if var not in collected_vars[role]['readme']:
            issues[role]['readme_not-in-readme'].append(var)
    for var in collected_vars[role]['readme']:
        # Declared in Readme, but absent in role
        if var not in role_var_names:
            issues[role]['readme_not-in-role'].append(var)
        # Declared in Readme, but absent in playbook
        if var not in pbook_vars[role]:
            issues[role]['readme_not-in-pbook'].append(var)


#
# Count number of issues...
#
issues_count = len(
    list(
        chain.from_iterable(
            list(
                chain.from_iterable(
                    [list(issues[x].values()) for x in issues]
                )
            )
        )
    )
)


#
# Show results
#
if not args.quiet:
    for role in issues:
        # Role/playbook issues
        for issue in issues[role].keys():
            if len(issues[role][issue]) > 0:
                print('\n[%s]' % role)
                break
        if len(issues[role]['absent']) > 0:
            print('''
            Declared in role, but missing in the playbook:
            ''')
            for var in issues[role]['absent']:
                print('\t -', var)
        if len(issues[role]['undeclared']) > 0:
            print('''
            Declared in playbook, but undeclared in the role:
            ''')
            for var in issues[role]['undeclared']:
                print('\t -', var)
        if len(issues[role]['defaults']) > 0:
            print('''
            Declared in playbook that are overwriting defaults:
            ''')
            for var in issues[role]['defaults']:
                print('\t -', var)
        # Readme issues
        if len(issues[role]['readme_not-in-readme']) > 0:
            print('''
            Declared in role, but absent in Readme:
            ''')
            for var in issues[role]['readme_not-in-readme']:
                print('\t -', var)
        if len(issues[role]['readme_not-in-role']) > 0:
            print('''
            Declared in Readme, but absent in role:
            ''')
            for var in issues[role]['readme_not-in-role']:
                print('\t -', var)
        if len(issues[role]['readme_not-in-pbook']) > 0:
            print('''
            Declared in Readme, but absent in playbook:
            ''')
            for var in issues[role]['readme_not-in-pbook']:
                print('\t -', var)
        # Type mismatch
        if len(issues[role]['type_mismatch']) > 0:
            print('''
            Type mismatch between the playbook and role:
            ''')
            for var in issues[role]['type_mismatch']:
                print('\t -', var)
    if issues_count > 0:
        print('\n\t%s issues in total.\n' % issues_count)


#
# Single integer output
#
if args.quiet and issues_count > 0:
    print(issues_count)
