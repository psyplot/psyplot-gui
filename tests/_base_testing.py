# -*- coding: utf-8 -*-
from unittest import TestCase
from psyplot_gui.compat.qtcompat import QApplication


class PsyPlotGuiTestCase(TestCase):
    """A base class for testing the psyplot_gui module

    At the initializzation of the TestCase, a new
    :class:`psyplot_gui.main.MainWindow` widget is created which is closed at
    the end of all the tests"""

    @classmethod
    def setUpClass(cls):
        cls._app = QApplication.instance()
        if cls._app is None:
            cls._app = QApplication([])
        cls._app.setQuitOnLastWindowClosed(False)

    @classmethod
    def tearDownClass(cls):
        QApplication.quit()

    def setUp(self):
        from psyplot_gui.main import MainWindow
        self.window = MainWindow.run()

    def tearDown(self):
        self.window.close()
        del self.window
