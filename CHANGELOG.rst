.. SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
..
.. SPDX-License-Identifier: CC-BY-4.0

v1.4.0
======
Compatibility fixes and LGPL license

As with psyplot 1.4.0, psyplot-gui is now continuously tested and deployed with
CircleCI.


Added
-----
- psyplot-gui does now have a CITATION.cff file, see https://citation-file-format.github.io


Changed
-------
- psyplot is now officially licensed under LGPL-3.0-only,
  see `#29 <https://github.com/psyplot/psyplot/pull/29>`__
- Documentation is now hosted with Github Pages at https://psyplot.github.io/psyplot-gui.
  Redirects from the old documentation at `https://psyplot-gui.readthedocs.io` have been
  configured.
- We use CicleCI now for a standardized CI/CD pipeline to build and test
  the code and docs all at one place, see `#28 <https://github.com/psyplot/psyplot-gui/pull/28>`__



v1.3.0
======
Presets and more variable info

Changed
-------
- psyplot-gui has been moved from https://github.com/Chilipp/psyplot-gui to https://github.com/psyplot/psyplot-gui,
  see `#10 <https://github.com/psyplot/psyplot-gui/pull/10>`__
- variables in the dataset tree show now more content,
  see `#16 <https://github.com/psyplot/psyplot-gui/pull/16>`__
- setting the rcparam ``help_explorer.use_intersphinx`` to None, will not use
  intersphinx on windows, see `#20 <https://github.com/psyplot/psyplot-gui/pull/20>`__

Added
-----
- The psyplot gui can now load and save preset files,
  see `psyplot#24 <https://github.com/psyplot/psyplot/pull/24>`__ and
  `#17 https://github.com/psyplot/psyplot-gui/pull/17`__
- Add option to start the GUI without importing QtWebEngineWidgets
  `#11 <https://github.com/psyplot/psyplot-gui/pull/11>`__
- Dockmixins (i.e. plugins) can now reimplement the `position_dock` method that
  controls where the dock is exactly placed in the GUI
  (see `#12 <https://github.com/psyplot/psyplot-gui/pull/12>`__)

v1.2.4
======
New release with better OpenGL support (see ``psyplot --help``)

v1.2.3
======
Minor release without major API changes.

v1.2.2
======
From now one, python 2.7 is not supported anymore.

Added
-----
- Added the possibility to change the central widget of the GUI
- Added `remove_plugin` method for psyplot GUI plugins

Changed
-------
- removed MacOS app folder in python dist

v1.2.1
======
monkey patch for ipykernel < 5.1.1 to fix
https://github.com/ipython/ipykernel/issues/370

v1.2.0
======
Changed
-------
- The HTML help explorer now also shows a table of contents in the intro
  and in the side bar to navigate to previously visited objects

v1.1.0
======
This release mainly adds the possibility to create plugins into the
psyplot-gui and it adds a new framework to allow the formatoptions to provide
a custom interface to the formatoptions widget.

Added
-----
- Added layout windows menu and default layout
- Added ``script`` and ``command`` command line arguments
- The ``pwd`` command line arguments now changes the working directory of the
  running GUI
- Added callbacks to the ``MainWindow`` class. This framework can be used on a
  low level to interact with the current GUI.
- The DataFrameEditor. A widget to display dataframes
- The implementation of the ``psyplot.plotter.Formatoption.get_fmt_widget``
  method. Formatoptions now can add a custom widget to the formatoptions widget


v1.0.1
======
.. image:: https://zenodo.org/badge/55793611.svg
   :target: https://zenodo.org/badge/latestdoi/55793611

Added
-----
- added changelog

Changed
-------
- fixed bug that prevented startup on Windows
