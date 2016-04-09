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
We highly recommend to use conda_ for installing psyplot_gui.

You can then install psyplot_gui simply via::

    $ conda install -c chilipp psyplot_gui

If you do not want to use PyQt4 (we indeed recommend to use PyQt5), you should
remove the ``'pyqt'`` and and ``'qt'`` package from anaconda::

    $ conda remove -y pyqt qt

You then have to install PyQt5 manually (see the installation page) or use
an inofficial anaconda channel, e.g. the spyder-ide::

    $ conda install -c spyder-ide pyqt5


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
- PyQt4_ or PyQt5_: Python bindings to the Qt_ software

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^
We furthermore recommend to use

- sphinx_>=1.3.5: To use all features of the interactive documentation access

.. _psyplot: http://psyplot.readthedocs.org/en/latest/installing.html
.. _qtconsole: https://qtconsole.readthedocs.org/en/latest/
.. _fasteners: http://fasteners.readthedocs.org/en/latest/index.html
.. _sphinx: http://www.sphinx-doc.org/en/stable/index.html
.. _PyQt4: http://pyqt.sourceforge.net/Docs/PyQt4/installation.html
.. _PyQt5: http://pyqt.sourceforge.net/Docs/PyQt5/installation.html
.. _Qt: http://www.qt.io/
