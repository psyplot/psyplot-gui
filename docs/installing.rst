.. SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
..
.. SPDX-License-Identifier: CC-BY-4.0

.. _install:

.. highlight:: bash

Installation
============
This package requires the psyplot package which is installed alongside if you
use ``conda`` or ``pip``. However see the psyplot_ documentation for further
informations.

How to install
--------------

Installation using conda
^^^^^^^^^^^^^^^^^^^^^^^^
We highly recommend to use conda_ for installing psyplot-gui.

You can then install psyplot-gui simply via::

    $ conda install -c conda-forge psyplot-gui


Installation using pip
^^^^^^^^^^^^^^^^^^^^^^
If you do not want to use conda for managing your python packages, you can also
use the python package manager ``pip`` and install via::

    $ pip install psyplot-gui


Dependencies
------------
Required dependencies
^^^^^^^^^^^^^^^^^^^^^
Psyplot has been tested for python 2.7 and >=3.7. Furthermore the package is
built upon multiple other packages, namely

- psyplot_>=1.4: The underlying framework for data visualization
- qtconsole_>=4.1.1: A package providing the necessary objects for running
  an inprocess ipython console in a Qt widget
- fasteners_: Which provides an inprocess lock to communicate to the psyplot
  mainwindow
- PyQt5_: Python bindings to the Qt_ software
- sphinx_>=1.3.5: To use all features of the interactive documentation access

.. _conda: https://docs.conda.io/en/latest/
.. _psyplot: https://psyplot.github.io/psyplot/installing.html
.. _qtconsole: https://qtconsole.readthedocs.io/en/latest/
.. _fasteners: https://fasteners.readthedocs.org/en/latest/index.html
.. _sphinx: https://www.sphinx-doc.org/en/master/index.html
.. _PyQt5: https://www.riverbankcomputing.com/static/Docs/PyQt5/installation.html
.. _Qt: https://www.qt.io/
