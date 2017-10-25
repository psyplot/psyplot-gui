# -*- coding: utf-8 -*-
"""Module defining the base class for the gui test"""
import os
import os.path as osp
import unittest

os.environ['PSYPLOT_PLUGINS'] = ('yes:psyplot_gui_test.plugin::'
                                 'yes:psy_simple.plugin')


from psyplot.config import setup_logging


test_dir = osp.dirname(__file__)
setup_logging(osp.join(test_dir, 'logging.yml'), env_key='')


from psyplot_gui.compat.qtcompat import QApplication
from psyplot_gui import rcParams
from psyplot import rcParams as psy_rcParams


on_travis = os.environ.get('TRAVIS')

rcParams.defaultParams['main.listen_to_port'][0] = False
rcParams.defaultParams['help_explorer.render_docs_parallel'][0] = False
rcParams.defaultParams['help_explorer.use_intersphinx'][0] = False
rcParams.defaultParams['plugins.include'][0] = ['psyplot_gui_test.plugin']
rcParams.defaultParams['plugins.exclude'][0] = 'all'
rcParams.update_from_defaultParams()


class PsyPlotGuiTestCase(unittest.TestCase):
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
        cls._app.quit()
        del cls._app

    def setUp(self):
        from psyplot_gui.main import MainWindow
        self.window = MainWindow.run(show=False)

    def tearDown(self):
        import psyplot.project as psy
        self.window.close()
        del self.window
        psy.close('all')
        rcParams.update_from_defaultParams()
        psy_rcParams.update_from_defaultParams()
        rcParams.disconnect()
        psy_rcParams.disconnect()

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
