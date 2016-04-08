.. _install:

Installation
============
This package requires the psyplot package which is installed alongside if you
use ``conda`` or ``pip``. However see the psyplot_ documentation for further
informations.

How to install
--------------

Installation using conda
^^^^^^^^^^^^^^^^^^^^^^^^
We highly recommend to use conda_ for installing psyplot_gui.
If you do not already have PyQt4 of PyQt5 installed, install PyQt4 via::

    $ conda install pyqt

You can then install psyplot_gui simply via::

    $ conda install -c chilipp psyplot_gui


Installation using pip
^^^^^^^^^^^^^^^^^^^^^^
If you do not want to use conda for managing your python packages, you can also
use the python package manager ``pip`` and install via::

    $ pip install psyplot_gui


Dependencies
------------
Required dependencies
^^^^^^^^^^^^^^^^^^^^^
Psyplot has been tested for python 2.7 and 3.4. Furthermore the package is
built upon multiple other packages, namely

- psyplot_>=0.2: The underlying framework for data visualization
- qtconsole_>=4.1.1: A package providing the necessary objects for running
  an inprocess ipython console in a Qt widget
- fasteners_: Which provides an inprocess lock to communicate to the psyplot
  mainwindow

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^
We furthermore recommend to use

- sphinx_>=1.3.5: To use all features of the interactive documentation access

.. _psyplot: http://psyplot.readthedocs.org/en/latest/installing.html
.. _qtconsole: https://qtconsole.readthedocs.org/en/latest/
.. _fasteners: http://fasteners.readthedocs.org/en/latest/index.html
.. _sphinx: http://www.sphinx-doc.org/en/stable/index.html
