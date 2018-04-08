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
