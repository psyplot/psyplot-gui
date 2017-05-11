"""Add the missing informations to the conda recipe and build the conda package

This script fills in the necessary informations into meta.yaml and builds the
conda package of the given package in the psyplot framework.

Call signature::

    python build_package.py <path-to-package>
"""
import os.path as osp
import sys
import yaml
import subprocess as spr
import pathlib
import argparse


def get_directory(s):
    return osp.dirname(osp.join(s, ''))

parser = argparse.ArgumentParser(
    description='Create a conda receipt from python source files')

parser.add_argument('package', help="The path to the Python package",
                    type=get_directory)
parser.add_argument('outdir', type=get_directory, help="""
    The output directory. The recipe will be in `outdir`/`basename package`. If
    this directory already contains a `meta.template` file, this one will be
    used.""")


args = parser.parse_args()


def file2html(fname):
    return pathlib.Path(osp.abspath(fname)).as_uri()


# Will be set down below from version.py
__version__ = None

#: The path to the package
path = args.package

#: The path for the output. It already has to include a file called
#: 'meta.template'. Otherwise, conda skeleton will be run
outdir = args.outdir


#: The name of the package
package = osp.basename(path)

#: Run setup.py sdist
spr.check_call([sys.executable, 'setup.py', 'sdist'],
               stdout=sys.stdout, stderr=sys.stderr, cwd=path)

# set __version__
with open(osp.join(path, package.replace('-', '_'), 'version.py')) as f:
    exec(f.read())

assert __version__ is not None, (
    "__version__ has not been set in version.py!")

version = __version__

template_file = osp.join(outdir, package, 'meta.template')

if osp.exists(template_file):
    # Read the meta.template
    with open(template_file) as f:
        meta = yaml.load(f)

    # fill in the missing informations
    meta['package']['version'] = version
    meta['source']['fn'] = package + '-' + version + '.tar.gz'
    meta['source']['url'] = file2html(osp.join(
        path, 'dist', meta['source']['fn']))

    # write out the recipe
    with open(osp.join('recipes', package, 'meta.yaml'), 'w') as f:
        yaml.dump(meta, f, default_flow_style=False)

else:

    spr.check_call(['conda', 'skeleton', 'pypi', '--manual-url',
                    file2html(osp.join(
                        path, 'dist', package + '-' + version + '.tar.gz')),
                    '--output-dir', outdir],
                   stdout=sys.stdout, stderr=sys.stderr)
