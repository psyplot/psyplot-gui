from setuptools import setup, find_packages


setup(name='psyplot_gui_test',
      version='1.0.0',
      license="GPLv2",
      packages=find_packages(exclude=['docs', 'tests*', 'examples']),
      entry_points={'psyplot_gui': ['w1=psyplot_gui_test.plugin:W1',
                                    'w2=psyplot_gui_test.plugin:W2'],
                    'psyplot': ['plugin=psyplot_gui_test.plugin']},
      zip_safe=False)
