Command line usage
==================
The ``psyplot_gui`` module extends the
`command line usage of the psyplot module`__. You can open one (or more) files
in the graphical user interface simply via::

    $ psyplot myfile.nc

By default, if the gui is already running, the file is opened in this gui
unless you specify the ``ni`` option.

.. highlight:: bash

.. argparse::
   :module: psyplot_gui
   :func: get_parser
   :prog: psyplot

.. _command line usage of the psyplot module: http://psyplot.readthedocs.org/en/latest/command_line.html
