#!/usr/bin/python

# Copyright (C) 2011  Centre de Recherche Astronomique de Lyon (CRAL)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     2. Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#     3. The name of AURA and its representatives may not be used to
#       endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY CRAL ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AURA BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#

# Prerequisites
# =============
#
# The various software required are:
#
#  * Python (version 2.6 or 2.7)
#  * IPython
#  * numpy (version 1.6.2 or above)
#  * scipy (version 0.10.1 or above)
#  * matplotlib (version 1.1.0 or above)
#  * astropy (version 0.4 or above)
#  * nose
#  * PIL
#  * numexpr
#  * python-development package
#  * pkg-config tool
#  * C numerics library
#  * C CFITSIO library
#  * C OpenMP library (optional)
#
# Installation
# ============
#
# To install the mpdaf package, you first run the *setup.py build* command to build everything needed to install:
#
#   /mpdaf$ python setup.py build
#
# The setup script tries to use pkg-config to find the correct compiler flags and library flags.
#
# Note that on MAC OS, openmp is not used by default because clang doesn't support OpenMp.
# To force it, the USEOPENMP environment variable can be set to anything except an empty string:
#
#  /mpdaf$ sudo USEOPENMP=0 CC=<local path of gcc> python setup.py build
#
#
# After building everything, you log as root and install everything from build directory:
#
#   root:/mpdaf$ python setup.py install
#
#
# setup.py informs you that the fusion package is not found. But it's just a warning, it's not blocking and you can continue to install mpdaf.
#
# To install the fusion submodule, log as root and run the *setup.py fusion* command::
#
#  root:/mpdaf$ python setup.py fusion
#
# Unit tests
# ==========
#
# The command *setup.py test* runs unit tests after in-place build::
#
#   /mpdaf$ python setup.py test


import os
import subprocess
import sys
# import setuptools

from distutils.core import setup, Command, Extension


#os.environ['DISTUTILS_DEBUG'] = '1'

class UnitTest(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        errno = subprocess.call(['nosetests', '-v', '-a speed=fast'])
        raise SystemExit(errno)


class MakeFusion(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import shutil
        import mpdaf.fusion
        subprocess.call(['make', '-C', 'lib/mpdaf/fusion/'])
        shutil.copy('lib/mpdaf/fusion/fusion_fit', '/usr/local/bin/fusion_fit')
        shutil.copy('lib/mpdaf/fusion/fusion_FSF', '/usr/local/bin/fusion_FSF')
        shutil.copy('lib/mpdaf/fusion/fusion_LSF', '/usr/local/bin/fusion_LSF')
        shutil.copy('lib/mpdaf/fusion/fusion_residual', '/usr/local/bin/fusion_residual')
        shutil.copy('lib/mpdaf/fusion/fusion_resampling', '/usr/local/bin/fusion_resampling')
        shutil.copy('lib/mpdaf/fusion/fusion_variance', '/usr/local/bin/fusion_variance')
        subprocess.call(['make', 'cleanall', '-C', 'lib/mpdaf/fusion/'])
        path = os.path.abspath(os.path.dirname(mpdaf.fusion.__file__))
        shutil.copy('lib/mpdaf/fusion/examples/LSF_V1.fits', path + '/LSF_V1.fits')

package_dir = {'mpdaf': 'lib/mpdaf/', 'mpdaf_user': 'mpdaf_user/'}
packages = ['mpdaf', 'mpdaf.tools', 'mpdaf.obj', 'mpdaf.drs', 'mpdaf.MUSE',
            'mpdaf_user', 'mpdaf.sdetect']
if os.path.isfile('lib/mpdaf/fusion/__init__.py'):
    packages.append('mpdaf.fusion')

for path in os.listdir('mpdaf_user'):
    if os.path.isdir('mpdaf_user/' + path + '/lib/' + path):
        package_dir['mpdaf_user.' + path] = 'mpdaf_user/' + path + '/lib/' + path
        packages.append('mpdaf_user.' + path)
    if os.path.isfile('mpdaf_user/' + path + '/__init__.py'):
        package_dir['mpdaf_user.' + path] = 'mpdaf_user/' + path + '/lib/'
        packages.append('mpdaf_user.' + path)
        #package_dir[path] = 'mpdaf_user/'+path
        # packages.append(path)
    if os.path.isfile('mpdaf_user/' + path + '/' + path + '.py'):
        package_dir['mpdaf_user.' + path] = 'mpdaf_user/' + path
        packages.append('mpdaf_user.' + path)


def options(*packages, **kw):
    flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}

    try:
        subprocess.check_output(["pkg-config", "--version"])
    except subprocess.CalledProcessError as e:
        sys.exit(e.output)
    except OSError as e:
        print 'pkg-config not installed ?'
        sys.exit(e)

    for package in packages:
        try:
            subprocess.check_call(["pkg-config", package])
        except subprocess.CalledProcessError as e:
            sys.exit("package '{}' not found.".format(package))

    for token in subprocess.check_output(["pkg-config", "--libs", "--cflags",
                                          ' '.join(packages)]).split():
        if token[:2] in flag_map:
            kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
        else:  # throw others to extra_link_args
            kw.setdefault('extra_link_args', []).append(token)

    kw.setdefault('libraries', []).append('m')

    # Use OpenMP if directed or not on a Mac
    if os.environ.get('USEOPENMP') or not sys.platform.startswith('darwin'):
        kw.setdefault('extra_link_args', []).append('-lgomp')
        kw.setdefault('extra_compile_args', []).append('-fopenmp')
    else:
        print "Unable to find OPENMP"

    for k, v in kw.iteritems():  # remove duplicated
        kw[k] = list(set(v))
    return kw


setup(name='mpdaf',
      version='1.1',
      description='MUSE Python Data Analysis Framework is a python framework '
      'in view of the analysis of MUSE data in the context of the GTO.',
      url='http://urania1.univ-lyon1.fr/mpdaf/login',
      requires=['numpy (>= 1.0)', 'scipy (>= 0.10)', 'matplotlib', 'astropy',
                'nose', 'PIL'],
      package_dir=package_dir,
      packages=packages,
      package_data={'mpdaf.drs': ['mumdatMask_1x1/*.fits.gz'], 'mpdaf.sdetect': ['muselet_data/*']},
      maintainer='Laure Piqueras',
      maintainer_email='laure.piqueras@univ-lyon1.fr',
      platforms='any',
      cmdclass={'test': UnitTest, 'fusion': MakeFusion},
      scripts=['lib/mpdaf/scripts/make_white_image.py'],
      ext_package='mpdaf',
      ext_modules=[Extension(
          'libCmethods',
          ['src/tools.c', 'src/subtract_slice_median.c', 'src/merging.c'],
          **options('cfitsio')
      )],
      )
