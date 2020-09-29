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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Operating System :: OS Independent',
      ],
      keywords=('visualization netcdf raster cartopy earth-sciences pyqt qt '
                'ipython jupyter qtconsole'),
      url='https://github.com/psyplot/psyplot-gui',
      author='Philipp S. Sommer',
      author_email='philipp.sommer@hzg.de',
      license="GPLv2",
      packages=find_packages(exclude=['docs', 'tests*', 'examples']),
      install_requires=[
          'psyplot>=1.3.0',
          'qtconsole',
          'fasteners',
          'sphinx>=2.4.0',
          'sphinx_rtd_theme',
      ],
      package_data={'psyplot_gui': [
          osp.join('psyplot_gui', 'sphinx_supp', 'conf.py'),
          osp.join('psyplot_gui', 'sphinx_supp', 'psyplot.rst'),
          osp.join('psyplot_gui', 'sphinx_supp', '_static', '*'),
          osp.join('psyplot_gui', 'icons', '*.png'),
          osp.join('psyplot_gui', 'icons', '*.svg'),
          ]},
      project_urls={
          'Documentation': 'https://psyplot.readthedocs.io/projects/psyplot-gui',
          'Source': 'https://github.com/psyplot/psyplot-gui',
          'Tracker': 'https://github.com/psyplot/psyplot-gui/issues',
      },
      include_package_data=True,
      tests_require=['pytest', 'psutil'],
      cmdclass={'test': PyTest},
      zip_safe=False)
