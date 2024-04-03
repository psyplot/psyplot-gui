.. SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
..
.. SPDX-License-Identifier: CC-BY-4.0

.. _command-line:

Command line usage
==================
The ``psyplot-gui`` module extends the
`command line usage of the psyplot module`_. You can open one (or more) files
in the graphical user interface simply via::

    $ psyplot myfile.nc

By default, if the gui is already running, the file is opened in this gui
unless you specify the ``ni`` option.

.. highlight:: bash

.. argparse::
   :module: psyplot_gui
   :func: get_parser
   :prog: psyplot

.. _command line usage of the psyplot module: http://psyplot.github.io/psyplot/command_line.html
