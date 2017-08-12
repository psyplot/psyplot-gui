.. _configuration:

Configuration of the GUI
========================

As psyplot is configured by the :attr:`psyplot.config.rcsetup.rcParams`,
psyplot-gui is configured by the :attr:`psyplot_gui.config.rcsetup.rcParams`
dictionary.

Both dictionaries can also be modified through the ``Preferences``
widget (on MacOS, ⌘ + , on Windows and Linux:
:menuselection:`Help --> Preferences`).

As for ``psyplot``, the rcParams are stored in the psyplot configuration
directory, which is, under Linux and OSX by default, located at
``$HOME/.config/psyplot`` and under Windows at ``$HOME/.psyplot``.
This file might look like

.. ipython::

    In [1]: from psyplot_gui import rcParams

    In [2]: print(rcParams.dump())
