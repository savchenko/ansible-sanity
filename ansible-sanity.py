#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Andrew Savchenko (c) Apache 2.0
# andrew@savchenko.net
#
import os
from argparse import ArgumentParser
from ast import literal_eval
from itertools import chain
from re import match

from yaml import safe_load as yaml_safe_load
from yaml.scanner import ScannerError

#
# Setup arguments parser
#
parser = ArgumentParser(
                       prog='ansible-sanity',
                       description='Sanity-checks between role, its playbooks and readme files.'
                       )
parser.add_argument('-p', '--playbook', help="Path to the playbook .YML file")
parser.add_argument('-c', '--consistency', action='store_true', help="Check variables consistency")
parser.add_argument('-b', '--become', action='store_true', help="Check that `become` has username defined")
parser.add_argument('-q', '--quiet', action='store_true', help="Output number of issues only")
args = parser.parse_args()


#      +------------------------------------+----------------------------+
#      | Task data   | Variables | Files    | Discovered issues          |
#      |-------------+-----------+----------|----------------------------|
#      | become      | playbook  | tasks    | become-user_without_become |
#      | become_user | defaults  | defaults | become_without_become-user |
#      | module      | vars      | vars     | overwrites_defaults        |
#      | name        | READMEs   | READMEs  | type_mismatch              |
#      |             |           |          | tasks_without_names        |
#      |             |           |          | in-readme_not-in-role      |
#      |             |           |          | in-readme_not-in-pbook     |
#      |             |           |          | in-role_not-in-readme      |
#      |             |           |          | in-playbook_not-in-role    |
#      |             |           |          | in-role_not-in-playbook    |
#      +-------------+-----------+----------+----------------------------+
#
collected: dict = {'playbook': {}, 'files': {}, 'roles': {}, 'issues': {}}


#
# Check user-supplied data
#
if args.playbook and args.playbook.endswith('.yml'):
    if os.path.isfile(args.playbook):
        pbook_dir = os.path.dirname(os.path.abspath(args.playbook))
    else:
        raise Exception("ERROR: Unable to open %s" % args.playbook)
else:
    parser.print_usage()
    os._exit(os.EX_NOINPUT)

#
# Fail gracefully
#
def noroles():
    print('No roles to parse in %s' % args.playbook)
    os._exit(os.EX_DATAERR)

def badroles(exc):
    print('Unable to parse %s:' % args.playbook)
    print('\t%s' % exc[2])
    os._exit(os.EX_DATAERR)

def nothing_to_check():
    print('Nothing to do. Are you calling this with the correct parameters?')
    os._exit(os.EX_NOINPUT)


if not args.consistency and not args.become:
    nothing_to_check()


#
# Open playbook, parse its content
#
with open(args.playbook, 'r') as pbook_yaml:
    try:
        pbook_yaml_parsed = yaml_safe_load(pbook_yaml)
    except ScannerError as exc:
        badroles(exc.args)
    pbook_name = os.path.basename(args.playbook)
    pbook_roles_added = []
    #
    #   REQUIREMENTS
    #
    #  - There is at least one (import|include)_role statement per Playbook task
    #  - No importing and including is happening in the same task simultaneously
    #  - No role is imported or included twice
    #
    for pbook_task_num, pbook_task in enumerate(pbook_yaml_parsed[0]['tasks']):
        if 'import_role' in pbook_task and 'include_role' in pbook_task:
                # Using task number in case it doesn't have a name
                print('Task #%s in %s has both `import_role` and `include_role`.'
                      % (pbook_task_num, pbook_name)
                )
        elif 'import_role' not in pbook_task and 'include_role' not in pbook_task:
                print('Task #%s in %s has neither `import_role` nor `include_role`.'
                      % (pbook_task_num, pbook_name),
                )
        # import_role
        elif 'import_role' in pbook_task:
            collected['playbook'][pbook_task['import_role']['name']] = pbook_task['vars']
            pbook_roles_added.append(pbook_task['import_role']['name'])
        # include_role
        elif 'include_role' in pbook_task:
            collected['playbook'][pbook_task['include_role']['name']] = pbook_task['vars']
            pbook_roles_added.append(pbook_task['include_role']['name'])
    pbook_yaml.close()


#
# Check for duplicates
#
if len(set(pbook_roles_added)) != len(pbook_roles_added):
    # We don't know which one is correct, hence the safe exit
    print('%s contains duplicated roles. Aborting.' % pbook_name)
    os._exit(os.EX_DATAERR)


#
# Collect files: tasks, vars, defaults and README.md
#
if len(collected['playbook']) > 0:
    for role in collected['playbook']:
        collected['files'][role] = { 'tasks': [], 'readme': [], 'vars': [], 'defaults': [] }
        role_path = os.path.join(os.path.dirname(os.path.normpath(args.playbook)), 'roles', role)
        role_readme = os.path.join(role_path, 'README.md')
        if os.path.isfile(role_readme):
            collected['files'][role]['readme'].append(role_readme)
        for root, dirs, files in os.walk(role_path):
            root_base = os.path.basename(os.path.normpath(root))
            if root_base  == 'vars':
                for f in files:
                    if f.endswith('.yaml') or f.endswith('.yml'):
                        collected['files'][role]['vars'].append(os.path.join(root, f))
            if root_base  == 'defaults':
                for f in files:
                    if f.endswith('.yaml') or f.endswith('.yml'):
                        collected['files'][role]['defaults'].append(os.path.join(root, f))
            if root_base == 'tasks':
                for f in files:
                    if f.endswith('.yaml') or f.endswith('.yml'):
                        collected['files'][role]['tasks'].append(os.path.join(root, f))
else:
    noroles()


#
# Collect tasks data: name, module, become and become_user
#
if args.become:
    for role in collected['files']:
        collected['roles'][role] = {'tasks': {}}
        for f in collected['files'][role]['tasks']:
            fname = os.path.basename(f)
            collected['roles'][role]['tasks'][fname] = {1: {}}
            try:
                with open(f, 'r') as f_yaml:
                    f_yaml_loaded = yaml_safe_load(f_yaml)
                    task_number = 0
                    for task in f_yaml_loaded:
                        task_number += 1
                        collected['roles'][role]['tasks'][fname][task_number] = {
                            'name': None,
                            'module': None,
                            'become': None,
                            'become_user': None
                        }
                        for k in ['name', 'become', 'become_user']:
                            if k in task:
                                collected['roles'][role]['tasks'][fname][task_number][k] = task.get(k, None)
                        task_enum = list(enumerate(task))
                        if not collected['roles'][role]['tasks'][fname][task_number]['name']:
                            collected['roles'][role]['tasks'][fname][task_number]['module'] = task_enum[0][1]
                        else:
                            if len(task_enum) > 1:
                                collected['roles'][role]['tasks'][fname][task_number]['module'] = task_enum[1][1]
            except TypeError:
                print('WARNING: ..' + f.split('roles')[1] + ' has no valid YAML content')


#
# Collect variables from default/vars and README.md
#
if args.consistency:
    for role in collected['files']:
        collected['roles'][role]['variables'] = {'vars': [], 'defaults': [], 'readme': []}
        var_def_rmd_files = [
            collected['files'][role]['vars'],
            collected['files'][role]['defaults'],
            collected['files'][role]['readme']
        ]
        for f in list(chain(*var_def_rmd_files)):
            if os.path.basename(os.path.abspath(os.path.join(f, os.pardir))) == 'vars':
                f_type = 'vars'
            elif os.path.basename(os.path.abspath(os.path.join(f, os.pardir))) == 'defaults':
                f_type = 'defaults'
            elif os.path.basename(f) == 'README.md':
                f_type = 'readme'
            else:
                raise Exception('ERROR: Unexpected element in the %s role' % collected['files'][role])
            if f_type != 'readme':
                with open(f, 'r') as f_yaml:
                    try:
                        f_yaml_loaded = yaml_safe_load(f_yaml)
                        for var in f_yaml_loaded:
                            collected['roles'][role]['variables'][f_type].append([var, type(f_yaml_loaded[var])])
                    except TypeError:
                        print('WARNING: ..' + f.split('roles')[1] + ' has no valid YAML content')
                f_yaml.close()
            else:
                with open(f, 'r') as f_readme:
                    f_lines = f_readme.readlines()
                    for ln in f_lines:
                        # ...
                        # | Variable | Description | Default |
                        # |----------+-------------+---------|
                        # | foo      | `foo` var   | 42      |
                        # ...
                        if match("^\|\s+\w+\s+\|\s+[^|]+\s+\|\s+[^|]+\s+\|$", ln):
                            if not match("\|\s+Variable\s+\|\s+Description\s+\|\s+Default\s+\|", ln):
                                readme_var = ln.split('|')[1].strip()
                                readme_value = ln.split('|')[3].strip()
                                try:
                                    readme_value = literal_eval(readme_value)
                                except (SyntaxError, BaseException):
                                    readme_value = literal_eval(repr(readme_value))
                                collected['roles'][role]['variables']['readme'].append([readme_var, readme_value])
                f_readme.close()


#
# Find issues
#
for role in collected['playbook']:
    collected['issues'][role] = {
        'overwrites_defaults': [],         # Declared in playbook and overwriting defaults
        'in-playbook_not-in-role': [],     # Declared in playbook, but undeclared in the role
        'in-role_not-in-playbook': [],     # Declared in role, but absent in playbook
        'in-role_not-in-readme': [],       # Declared in role, but absent in Readme
        'in-readme_not-in-role': [],       # Declared in Readme, but absent in role
        'in-readme_not-in-playbook': [],   # Declared in Readme, but absent in playbook
        'type_mismatch': [],               # Type mismatch between the playbook and role
        'become_without_become-user': [],  # `become` without `become_user`
        'become-user_without_become': [],  # `become_user` without `become`
        'tasks_without_names': []          # Tasks without `- name:`
    }
    if args.consistency:
        # variables declared in ../vars/*.yml
        role_var_names = [v[0] for v in collected['roles'][role]['variables']['vars']]
        for var in [var for var in collected['playbook'][role]]:
            # Declared in playbook, but undeclared in the role
            if var not in role_var_names and var not in collected['roles'][role]['variables']['defaults']:
                collected['issues'][role]['in-playbook_not-in-role'].append(var)
            # Declared in playbook and overwriting defaults
            if var in collected['roles'][role]['variables']['defaults']:
                collected['issues'][role]['overwrites_defaults'].append(var)
            # Type mismatch between the playbook and role
            for cvar in collected['roles'][role]['variables']['vars']:
                if cvar[0] == var:
                    if type(collected['playbook'][role][var]) != cvar[1]:
                        collected['issues'][role]['type_mismatch'].append(cvar[0])
        for var in role_var_names:
            # Declared in role, but absent in playbook
            if var not in collected['playbook'][role]:
                collected['issues'][role]['in-role_not-in-playbook'].append(var)
            # Declared in role, but absent in Readme
            if var not in [v[0] for v in collected['roles'][role]['variables']['readme']]:
                collected['issues'][role]['in-role_not-in-readme'].append(var)
        for var in [v[0] for v in collected['roles'][role]['variables']['readme']]:
            # Declared in Readme, but absent in role
            if var not in role_var_names:
                collected['issues'][role]['in-readme_not-in-role'].append(var)
            # Declared in Readme, but absent in playbook
            if var not in [v for v in collected['playbook'][role]]:
                collected['issues'][role]['in-readme_not-in-playbook'].append(var)
    if args.become:
        for f in collected['roles'][role]['tasks']:
            for task_number in collected['roles'][role]['tasks'][f]:
                # Nonames
                if not collected['roles'][role]['tasks'][f][task_number]['name']:
                    collected['issues'][role]['tasks_without_names'].append(
                        '(%s/%s) "%s" from %s' % (
                            task_number,
                            len(collected['roles'][role]['tasks'][f]),
                            collected['roles'][role]['tasks'][f][task_number]['module'], f,
                        )
                    )
                # Become-no-user
                if collected['roles'][role]['tasks'][f][task_number]['become'] not in [None, False] and \
                        not isinstance(collected['roles'][role]['tasks'][f][task_number]['become_user'], str):
                            collected['issues'][role]['become_without_become-user'].append(
                                '(%s/%s) "%s" from %s' % (
                                    task_number, len(collected['roles'][role]['tasks'][f]),
                                    collected['roles'][role]['tasks'][f][task_number]['module'], f,
                                )
                            )
                # Become-no-become (or `become` is False)
                if collected['roles'][role]['tasks'][f][task_number]['become_user'] is not None and \
                        not isinstance(collected['roles'][role]['tasks'][f][task_number]['become'], bool) or \
                        collected['roles'][role]['tasks'][f][task_number]['become'] is False:
                            collected['issues'][role]['become-user_without_become'].append(
                                '(%s/%s) "%s" from %s' % (
                                    task_number, len(collected['roles'][role]['tasks'][f]),
                                    collected['roles'][role]['tasks'][f][task_number]['module'], f,
                                )
                            )


#
# Count number of issues...
#
issues_count = len(
    list(
        chain.from_iterable(
            list(
                chain.from_iterable(
                    [list(collected['issues'][issue].values()) for issue in collected['issues']]
                )
            )
        )
    )
)

#
# Show results
#
if issues_count > 0:
    if not args.quiet:
        stdout = []
        for role in collected['issues']:
            # Role/playbook
            for issue in collected['issues'][role].keys():
                if len(collected['issues'][role][issue]) > 0:
                    stdout.append('\n\033[92m[%s]\033[0m' % role)
                    break
            if len(collected['issues'][role]['in-role_not-in-playbook']) > 0:
                stdout.append('\nDeclared in the role, but missing in the playbook:\n')
                for var in collected['issues'][role]['in-role_not-in-playbook']:
                    stdout.append('   - %s' % var)
            if len(collected['issues'][role]['in-playbook_not-in-role']) > 0:
                stdout.append('\nDeclared in the playbook, but undeclared in the role:\n')
                for var in collected['issues'][role]['in-playbook_not-in-role']:
                    stdout.append('   - %s' % var)
            if len(collected['issues'][role]['overwrites_defaults']) > 0:
                stdout.append('\nDeclared in the playbook and are overwriting defaults:\n')
                for var in collected['issues'][role]['overwrites_defaults']:
                    stdout.append('   - %s' % var)
            # Readme
            if len(collected['issues'][role]['in-role_not-in-readme']) > 0:
                stdout.append('\nDeclared in the role, but absent in its README.md:\n')
                for var in collected['issues'][role]['in-role_not-in-readme']:
                    stdout.append('   - %s' % var)
            if len(collected['issues'][role]['in-readme_not-in-role']) > 0:
                stdout.append('\nDeclared in the README.md, but absent in the role:\n')
                for var in collected['issues'][role]['in-readme_not-in-role']:
                    stdout.append('   - %s' % var)
            if len(collected['issues'][role]['in-readme_not-in-playbook']) > 0:
                stdout.append('\nDeclared in the README.md, but absent in the playbook:\n')
                for var in collected['issues'][role]['in-readme_not-in-playbook']:
                    stdout.append('   - %s' % var)
            # Type mismatch
            if len(collected['issues'][role]['type_mismatch']) > 0:
                stdout.append('\nType mismatch between the playbook and role:\n')
                for var in collected['issues'][role]['type_mismatch']:
                    stdout.append('   - %s' % var)
            # Noname
            if len(collected['issues'][role]['tasks_without_names']) > 0:
                stdout.append('\nNameless tasks:\n')
                for var in collected['issues'][role]['tasks_without_names']:
                    stdout.append('   - %s' % var)
            # Become-no-user
            if len(collected['issues'][role]['become_without_become-user']) > 0:
                stdout.append('\n`become` without explicitly set `become_user`:\n')
                for var in collected['issues'][role]['become_without_become-user']:
                    stdout.append('   - %s' % var)
            # Become-no-become
            if len(collected['issues'][role]['become-user_without_become']) > 0:
                stdout.append('\n`become_user` without `become` set to True:\n')
                for var in collected['issues'][role]['become-user_without_become']:
                    stdout.append('   - %s' % var)
        stdout.append('\n\033[91m%s issues in total.\033[0m\n' % issues_count)
        print(*stdout, sep='\n')
#
# `-q` flag, single integer output
#
if args.quiet:
    print(issues_count)
