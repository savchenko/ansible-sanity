#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Andrew Savchenko (c) Apache 2.0
# andrew@savchenko.net

import os
import re
import argparse


parser = argparse.ArgumentParser(prog='ansible-unifier',
                                 description='Unifies quotation and booleans in a way that doesn\'t explode')
parser.add_argument('-d', '--dir', help="Path to the ../roles/ directory")
parser.add_argument('-q', '--quiet', action='store_true', help="Output nothing except of the issues count")
args = parser.parse_args()


if os.path.isdir(args.dir):
    ymls = []
    ymls_changed = 0
else:
    raise Exception('ERROR: Unable to access %s' % args.dir)


for root, dirs, files in os.walk(args.dir):
    root_base = os.path.basename(os.path.normpath(root))
    for f in files:
        if f.endswith('.yml') or f.endswith('.yaml'):
            ymls.append(os.path.join(root, f))


for f in ymls:
    f_changed = False
    with open(f, 'r+') as fop:
        f_lines = fop.readlines()
        f_newlines = []
        for ln in f_lines:
            if '"' in ln:
                ln_match = re.search(r'(.+)(\w:\s+)(\")(.+?)(\")(.*)', ln)
                if ln_match:
                    if len(ln_match.groups()) == 6:
                        oldline = list(ln_match.groups())
                        if "'" in oldline[3]:
                            oldline[3] = re.sub(r"'", '"', oldline[3])
                        oldline[2] = oldline[4] = "'"
                        oldline_last = ''.join(oldline[-1:])
                        if not oldline_last.endswith('\n'):
                            oldline[-1:] = oldline_last + '\n'
                        [str(x) for x in oldline]
                        ln = ''.join(oldline)
                        f_changed = True
            if 'yes' in ln.lower():
                ln_orig = ln
                ln = re.sub(r": yes$", ': True', ln)
                if ln != ln_orig:
                    f_changed = True
            if 'no' in ln.lower():
                ln_orig = ln
                ln = re.sub(r": no$", ': False', ln)
                if ln != ln_orig:
                    f_changed = True
            f_newlines.append(ln)
        if f_changed:
            fop.seek(0, 0)
            fop.truncate()
            fop.writelines(f_newlines)
            fop.close()
            ymls_changed += 1
            if not args.quiet:
                print('Re-writing ../%s' % os.path.relpath(fop.name, args.dir))


if ymls_changed > 0 and not args.quiet:
    print('Unified %s YAMLs' % ymls_changed)
elif args.quiet:
    print(ymls_changed)
