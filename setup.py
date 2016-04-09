from setuptools import setup, find_packages
#import sys

#needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
#pytest_runner = ['pytest-runner'] if needs_pytest else []


def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='psyplot_gui',
      version='0.0.1dev',
      description='Graphical user interface for the psyplot package',
      long_description=readme(),
      classifiers=[
        'Development Status :: 4 - Beta',
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
        'Operating System :: OS Independent',
      ],
      keywords=('visualization netcdf raster cartopy earth-sciences pyqt qt'
                'ipython jupyter qtconsole'),
      url='https://github.com/Chilipp/psyplot_gui',
      author='Philipp Sommer',
      author_email='philipp.sommer@unil.ch',
      license="GPLv2",
      packages=find_packages(exclude=['docs', 'tests*', 'examples']),
      install_requires=[
          'psyplot',
          'qtconsole',
          'fasteners',
      ],
#      setup_requires=pytest_runner,
#      tests_require=['pytest'],
      zip_safe=False)
