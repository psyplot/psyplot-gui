#!/usr/bin/env python
"""Deploy anaconda builds to anaconda cloud

This script is designed for appveyor to deploy the build to anaconda cloud
using the token from the CONDA_REPO_TOKEN environment variable"""
import os.path as osp
import os
import six
import glob
import subprocess as spr

if six.PY2:
    FileExistsError = OSError

fname = glob.glob(osp.join(
    os.getenv('PYTHON'), 'conda-bld\win-64\psyplot-gui-*.tar.bz2'))[0]

try:
    os.makedirs('builds')
except FileExistsError:  # directory exists already
    pass

print('Start conversion of %s' % fname)

spr.call(['conda', 'convert', fname, '-p', 'win-32', '-o', 'builds'])

print('Done')

files = [fname] + glob.glob(osp.join('builds', 'win-32', '*'))

print('Uploading %s' % files)

p = spr.Popen(
    ['anaconda', '-t', os.getenv('CONDA_REPO_TOKEN'), 'upload'] + files,
    stdout=spr.PIPE, stderr=spr.PIPE)

p.wait()

print(p.stdout.read().decode('utf-8').replace(
    os.getenv('CONDA_REPO_TOKEN'), '<secure>'))

if p.poll():
    print(p.stderr.read().decode('utf-8').replace(
        os.getenv('CONDA_REPO_TOKEN'), '<secure>'))
    raise ValueError("Failed to deploy to anaconda cloud!")
