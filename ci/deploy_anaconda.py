#!/usr/bin/env python
"""Deploy anaconda builds to anaconda cloud

This script is designed for appveyor to deploy the build to anaconda cloud
using the token from the CONDA_REPO_TOKEN environment variable"""
import os.path as osp
import os
import glob
import subprocess as spr

fname = spr.check_output(
    ['conda', 'build', osp.join('ci', 'conda_recipe'), '--output',
     '--python', os.getenv('PYTHON_VERSION')]).decode(
        'utf-8').strip()

spr.check_call(['conda', 'convert', fname, '-p', 'win-32'])

p = spr.Popen(
    ['anaconda', '-t', os.getenv('CONDA_REPO_TOKEN'), 'upload', fname] +
    glob.glob(osp.join('win-32', '*')), stdout=spr.PIPE, stderr=spr.PIPE)

p.wait()

print(p.stdout.read().decode('utf-8').replace(
    os.getenv('CONDA_REPO_TOKEN'), '<secure>'))

if p.poll():
    print(p.stderr.read().decode('utf-8').replace(
        os.getenv('CONDA_REPO_TOKEN'), '<secure>'))
    raise ValueError("Failed to deploy to anaconda cloud!")
