# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

# -*- coding: utf-8 -*-
"""Module defining the base class for the gui test"""
import os
import os.path as osp
import unittest

from psyplot import rcParams as psy_rcParams
from psyplot.config import setup_logging

from psyplot_gui import rcParams
from psyplot_gui.compat.qtcompat import QApplication

os.environ["PSYPLOT_PLUGINS"] = (
    "yes:psyplot_gui_test.plugin::" "yes:psy_simple.plugin"
)


test_dir = osp.dirname(__file__)
setup_logging(osp.join(test_dir, "logging.yml"), env_key="")


def is_running_in_gui():
    from psyplot_gui.main import mainwindow

    return mainwindow is not None


running_in_gui = is_running_in_gui()


on_travis = os.environ.get("TRAVIS")


def setup_rcparams():
    rcParams.defaultParams["console.start_channels"][0] = False
    rcParams.defaultParams["main.listen_to_port"][0] = False
    rcParams.defaultParams["help_explorer.render_docs_parallel"][0] = False
    rcParams.defaultParams["help_explorer.use_intersphinx"][0] = False
    rcParams.defaultParams["plugins.include"][0] = ["psyplot_gui_test.plugin"]
    rcParams.defaultParams["plugins.exclude"][0] = "all"
    rcParams.update_from_defaultParams()


if running_in_gui:
    app = QApplication.instance()
else:
    setup_rcparams()
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)


class PsyPlotGuiTestCase(unittest.TestCase):
    """A base class for testing the psyplot_gui module

    At the initializzation of the TestCase, a new
    :class:`psyplot_gui.main.MainWindow` widget is created which is closed at
    the end of all the tests"""

    @classmethod
    def setUpClass(cls):
        from psyplot_gui.main import mainwindow

        cls._close_app = mainwindow is None
        cls._app = app
        if not running_in_gui:
            import psyplot_gui

            psyplot_gui.UNIT_TESTING = True

    @classmethod
    def tearDownClass(cls):
        del cls._app

    def setUp(self):
        import psyplot_gui.main as main

        if not running_in_gui:
            setup_rcparams()
            self.window = main.MainWindow.run(show=False)
        else:
            self.window = main.mainwindow

    def tearDown(self):
        import matplotlib.pyplot as plt
        import psyplot.project as psy

        if not running_in_gui:
            import psyplot_gui.main as main

            self.window.close()
            rcParams.update_from_defaultParams()
            psy_rcParams.update_from_defaultParams()
            rcParams.disconnect()
            psy_rcParams.disconnect()
            main._set_mainwindow(None)
        del self.window
        psy.close("all")
        plt.close("all")

    def get_file(self, fname):
        """Get the path to the file `fname`

        Parameters
        ----------
        fname: str
            The path of the file name (relative to the test directory)

        Returns
        -------
        str
            The complete path to the given file"""
        return osp.join(test_dir, fname)
