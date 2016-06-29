# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
from subprocess import check_output

LICENSE = """\
\"\"\"
Copyright (c) 2010-2016 CNRS / Centre de Recherche Astrophysique de Lyon

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
\"\"\"
"""

GIT_CMD = 'git shortlog -sen {} | cut -f1 --complement'


def modify(lines, license, start=0):
    print('Modify license text ... ', end='')
    for i, l in enumerate(lines[1:], 1):
        if l == '"""\n':
            end = i
            break

    newlines = license + lines[end+1:]
    if start == 1:
        newlines.insert(0, lines[0])
    return newlines


def insert(lines, license, pos=1):
    print('Insert license text ... ', end='')
    return lines[:pos] + license + lines[pos:]


if __name__ == "__main__":
    files = sys.argv[1:]

    for filename in files:
        print('- {} : '.format(filename), end='')
        with open(filename, 'r') as f:
            lines = f.readlines()

        if len(lines) == 0:
            print('Empty')
            continue

        authors = check_output(GIT_CMD.format(filename), shell=True)
        authors = ['Copyright (c) 2010-2016 {}\n'.format(author)
                   for author in authors.splitlines()]
        license = LICENSE.splitlines(True)
        license = license[:2] + authors + license[2:]

        if lines[0].startswith('"""Copyright'):
            lines = modify(lines, license)
        elif lines[1].startswith('"""Copyright'):
            lines = modify(lines, license, start=1)
        elif lines[0].startswith('# -*- coding'):
            lines = insert(lines, license)

        with open(filename, 'w') as f:
            f.write(''.join(lines))

        print('OK')
