import os.path as osp
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys


def readme():
    with open('README.rst') as f:
        return f.read()


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


# read the version from version.py
with open(osp.join('psyplot_gui', 'version.py')) as f:
    exec(f.read())


setup(name='psyplot-gui',
      version=__version__,
      description='Graphical user interface for the psyplot package',
      long_description=readme(),
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: OS Independent',
      ],
      keywords=('visualization netcdf raster cartopy earth-sciences pyqt qt '
                'ipython jupyter qtconsole'),
      url='https://github.com/Chilipp/psyplot-gui',
      author='Philipp Sommer',
      author_email='philipp.sommer@unil.ch',
      license="GPLv2",
      packages=find_packages(exclude=['docs', 'tests*', 'examples']),
      install_requires=[
          'psyplot>1.0.1',
          'qtconsole',
          'fasteners',
          'sphinx',
          'sphinx_rtd_theme',
      ],
      package_data={'psyplot_gui': [
          osp.join('psyplot_gui', 'sphinx_supp', 'conf.py'),
          osp.join('psyplot_gui', 'sphinx_supp', 'psyplot.rst'),
          osp.join('psyplot_gui', 'sphinx_supp', '_static', '*'),
          osp.join('psyplot_gui', 'icons', '*.png'),
          # mac app files
          osp.join('psyplot_gui', 'app', 'Psyplot.app', 'Contents', '*'),
          osp.join('psyplot_gui', 'app', 'Psyplot.app', 'Contents',
                   'Resources', '*'),
          osp.join('psyplot_gui', 'app', 'Psyplot.app', 'Contents',
                   'MacOS', '*'),
          ]},
      include_package_data=True,
      tests_require=['pytest'],
      cmdclass={'test': PyTest},
      zip_safe=False)
