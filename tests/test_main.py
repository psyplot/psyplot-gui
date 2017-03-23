"""Test utilities for the :mod:`psyplot_gui.main` module
"""
import unittest
import _base_testing as bt


class TestMainWindow(bt.PsyPlotGuiTestCase):

    def test_plugin(self):
        from psyplot_gui.main import mainwindow
        try:
            from psyplot_gui_test.plugin import W1, W2
        except ImportError:
            self.skipTest("Test plugin not installed")
        self.assertIn('psyplot_gui_test.plugin:W1:w1', mainwindow.plugins)
        self.assertIn('psyplot_gui_test.plugin:W2:w2', mainwindow.plugins)
        self.assertIsInstance(
            mainwindow.plugins['psyplot_gui_test.plugin:W1:w1'], W1)
        self.assertIsInstance(
            mainwindow.plugins['psyplot_gui_test.plugin:W2:w2'], W2)
        w = mainwindow.plugins['psyplot_gui_test.plugin:W2:w2']
        a = w.dock.toggleViewAction()
        # the plugin should be hidden
        self.assertFalse(a.isChecked())
        w.show_plugin()
        self.assertTrue(a.isChecked())


if __name__ == "__main__":
    unittest.main()
