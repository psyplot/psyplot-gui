.. SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
..
.. SPDX-License-Identifier: CC-BY-4.0

.. currentmodule:: psyplot_gui.main

.. _plugins:

Plugin configuration
====================

The psyplot GUI has several built-in plugins, e.g. the
:attr:`~MainWindow.help_explorer` or the :attr:`~MainWindow.fmt_widget`.
External libraries can :ref:`add plugins <develop-plugins>` and the user can
disable or enable them with through the :ref:`configuration <plugin-config>`.

.. note::

    These plugins should only affect the GUI. For other plugins that define
    new plotmethods, etc., see the
    :ref:`psyplot documentation <psyplot:plugins>`

.. _plugin-config:

Plugin configuration
--------------------
You can include and exclude plugins either through the ``include-plugins`` and
``exclude-plugins`` command line option (see :ref:`command-line`), or you
do it permanently with the :attr:`~psyplot_gui.config.rcsetup.rcParams` (see
:ref:`configuration`).

.. _develop-plugins:

Developing plugins
------------------
External libraries insert the GUI as an entry point. In the ``setup.py``
script of a package, include the following:

.. code-block:: python

    setup(
        ...,
        entry_points={
            "psyplot_gui": [
                "widget-name1=widget-module1:widget-class-name1",
                "widget-name2=widget-module2:widget-class-name2",
                ...,
            ],
        },
        ...,
    )

Here, `widget-name1` is an arbitrary name you want to assign to the widget,
`widget-module1` is the module from where to import the plugin, and
`widget-class-name1` is the name of the class that inherits the
:class:`psyplot_gui.common.DockMixin` class.

For the :attr:`~MainWindow.help_explorer`, this, for example, would like like

.. code-block:: python

    setup(
        ...,
        entry_points={
            "psyplot_gui": [
                "help=psyplot_gui.help_explorer:HelpExplorer",
            ],
        },
        ...,
    )
